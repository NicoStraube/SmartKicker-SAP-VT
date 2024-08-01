import json
import threading
import time

import cv2
import numpy as np
from ximea import xiapi


class DetectionThread(threading.Thread):

    def __init__(self, client_socket):
        super().__init__()
        self.client_socket = client_socket
        self.stop_event = threading.Event()

    def detect_red_color(frame):

        lower_red = np.array([0, 0, 0])
        upper_red = np.array([10, 255, 255])

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        mask = cv2.inRange(hsv, lower_red, upper_red)

        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        contours = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

        if len(contours) > 0:
            largest_contour = max(contours, key=cv2.contourArea)

            x, y, w, h = cv2.boundingRect(largest_contour)

            center_x = x + w // 2
            center_y = y + h // 2

            return center_x, center_y
        else:
            return None, None

    def detect_goal(center_x, center_y, last_goal_time, goal_box_left, goal_box_right):
        if center_x is None or center_y is None:
            return "", last_goal_time
        if (time.time() - last_goal_time) < 3:
            return "", last_goal_time

        if goal_box_left[0][0] <= center_x <= goal_box_left[1][0] and goal_box_left[0][1] <= center_y <= \
                goal_box_left[1][1]:
            return "black", time.time()
        elif goal_box_right[0][0] <= center_x <= goal_box_right[1][0] and goal_box_right[0][1] <= center_y <= \
                goal_box_right[1][1]:
            return "white", time.time()
        else:
            return "", last_goal_time

    def calculate_speed(positions, time_interval):

        DISTANCE_BETWEEN_GOALS_METERS = 1.2
        DISTANCE_BETWEEN_GOALS_PIXELS = 512

        x = positions[-1][0]
        y = positions[-1][1]
        prev_x = positions[-2][0]
        prev_y = positions[-2][1]

        distance = np.sqrt((x - prev_x) ** 2 + (y - prev_y) ** 2)

        distance = distance * DISTANCE_BETWEEN_GOALS_METERS / DISTANCE_BETWEEN_GOALS_PIXELS
        speed = distance / time_interval

        speed = speed * 3.6

        return speed, distance

    def get_direction(positions):
        if len(positions) > 3:
            x = positions[-1][0]
            y = positions[-1][1]
            prev_x = positions[-2][0]
            prev_y = positions[-2][1]

            xDirection = x - prev_x
            yDirection = y - prev_y

            return xDirection, yDirection
        else:
            return 0, 0

    def get_direction_delta(directions):
        if len(directions) > 3:
            xDelta = abs(directions[-2][0] - directions[-1][0])
            yDelta = abs(directions[-2][1] - directions[-1][1])

            return xDelta, yDelta
        else:
            return 0, 0

    def run(self):
        cam = xiapi.Camera()

        cam.open_device_by_SN('20851151')
        cam.set_imgdataformat('XI_RGB24')
        # cam.set_exposure(5000) # old: 20000; unused, because of auto-exposure/auto-gain
        img = xiapi.Image()
        cam.start_acquisition()
        cam.set_downsampling('XI_DWN_2x2')
        # cam.disable_aeag() auto-exposure/auto-gain
        cam.enable_aeag()  # "Exposure and gain will be used (50%:50%)
        print('SmartKicker_DEBUG: default AEAG_value is %i' % cam.get_aeag_level())
        cam.set_aeag_level(15)
        print('SmartKicker_DEBUG: AEAG_value after change %i' % cam.get_aeag_level())
        cam.disable_bpc()
        cam.disable_auto_wb()
        cam.set_height(310)
        cam.set_offsetY(90)
        cam.disable_ffc()

        framerate = cam.get_framerate_maximum()
        cam.set_framerate(framerate)
        print('SmartKicker_DEBUG: Framerate set to %i' % framerate)

        starting_time = time.time()
        frame_count = 0

        positions = []
        directions = []
        ball_was_shot = False
        last_shot_x = None
        last_shot_y = None
        goals_black = 0
        goals_white = 0
        current_score = ""

        last_timestamps = []

        last_goal_time = 0.0
        # host = "192.168.248.132"
        # port = 2024

        try:
            goal_box_left = [(50, 105), (89, 205)]
            goal_box_right = [(600, 105), (640, 205)]

            print('Waiting for ball movement.')
            while not self.stop_event.is_set():
                cam.get_image(img)

                frame = img.get_image_data_numpy()

                #    end_time = time.time()
                #    fps = 1/(end_time - starting_time)
                #   print("FPS:", fps)
                #    starting_time = end_time

                center_x, center_y = DetectionThread.detect_red_color(frame)
                if center_x != None:
                    positions.append((center_x, center_y))
                    xDirection, yDirection = DetectionThread.get_direction(positions)
                    directions.append((xDirection, yDirection))
                    xDelta, yDelta = DetectionThread.get_direction_delta(directions)
                    last_timestamps.append(time.time())
                    if len(last_timestamps) > 20:
                        last_timestamps.pop(0)

                    if xDelta > 10 or yDelta > 10:
                        last_shot_x = center_x
                        last_shot_y = center_y
                        ball_wasshot = True
                        print('SmartKicker_DEBUG: ball_wasshot: true')
                    else:
                        ball_was_shot = False
                        # print('SmartKicker_DEBUG: ball_wasshot: false')

                    team, last_goal_time = DetectionThread.detect_goal(center_x, center_y, last_goal_time,
                                                                       goal_box_left, goal_box_right)
                    if team != "":
                        if len(positions) > 10:
                            last_speed_measurements = []
                            average_speed = None
                            speed, distance = DetectionThread.calculate_speed(positions,
                                                                              last_timestamps[-1] - last_timestamps[-2])
                            print("Speed: ", speed)
                            if team == "black":
                                goals_black += 1
                            else:
                                goals_white += 1
                            current_score = f"{goals_black} : {goals_white}"
                            print(current_score)
                            data = {"player": team, "speed": speed, "score": current_score}

                            try:
                                self.client_socket.sendall(json.dumps(data).encode("utf-8"))
                            except Exception as e:
                                print(e)

                    if len(positions) > 20:
                        positions.pop(0)
                        directions.pop(0)

                    if center_x != None:
                        cv2.circle(frame, (center_x, center_y), 15, (255, 0, 0), -1)

                cv2.rectangle(frame, goal_box_left[0], goal_box_left[1], (0, 255, 0), 2)
                cv2.rectangle(frame, goal_box_right[0], goal_box_right[1], (0, 255, 0), 2)

                # remove while production
                cv2.imshow("Frame", frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break


        except Exception as e:
            print(e)
        finally:
            cam.close_device()

    def stop(self):
        self.stop_event.set()
