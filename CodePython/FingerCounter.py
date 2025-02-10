import time
import cv2
import HandTrackingModule as htm
import paho.mqtt.client as mqtt
import urllib.request
import json
import os

# Tên file lưu trạng thái
STATE_FILE = "relay_led_state.json"
# Hàm lưu trạng thái relay và LED vào file
def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# Hàm đọc trạng thái relay và LED từ file
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"relay": 0, "led_state1": 0, "led_state2": 0}  # Giá trị mặc định

# Khôi phục trạng thái
state = load_state()
relay = state.get("relay", 0)
led_state1 = state.get("led_state1", 0)
led_state2 = state.get("led_state2", 0)

# Trước khi thoát chương trình, lưu trạng thái
import atexit

@atexit.register
def on_exit():
    save_state({"relay": relay, "led_state1": led_state1, "led_state2": led_state2})
# Cấu hình MQTT
mqttBroker = "broker.hivemq.com"
client = mqtt.Client("client_name")
client.connect(mqttBroker)

# Cấu hình camera
url = "http://192.168.158.166:81/stream"  # Kiểm tra với cổng khác nếu cần
cap = cv2.VideoCapture(url)
# Kiểm tra nếu video stream mở thành công
if not cap.isOpened():
    print("Không thể mở video stream.")
    exit()

cap.set(3, 960)  # Chỉnh độ rộng (width)
cap.set(4, 720)  # Chỉnh độ cao (height)

wCam, hCam = 640, 480  # Cập nhật lại độ phân giải của ảnh

# Khởi tạo bộ phát hiện tay
detector = htm.handDetector(detectionCon=int(0.85))
tipIds = [4, 8, 12, 16, 20]
# Tải hình ảnh cử chỉ tay

like_img = cv2.imread("images/like.png", cv2.IMREAD_UNCHANGED)
dislike_img = cv2.imread("images/dislike.png", cv2.IMREAD_UNCHANGED)
ilu_img = cv2.imread("images/ilu.png", cv2.IMREAD_UNCHANGED)
bay_img = cv2.imread("images/7.png", cv2.IMREAD_UNCHANGED)
ok_img = cv2.imread("images/ok.png", cv2.IMREAD_UNCHANGED)
y_img = cv2.imread("images/y.png", cv2.IMREAD_UNCHANGED)
N0_img = cv2.imread("images/0.png", cv2.IMREAD_UNCHANGED)
N1_img = cv2.imread("images/1.png", cv2.IMREAD_UNCHANGED)
N2_img = cv2.imread("images/2.png", cv2.IMREAD_UNCHANGED)
N3_img = cv2.imread("images/3.png", cv2.IMREAD_UNCHANGED)
N4_img = cv2.imread("images/4.png", cv2.IMREAD_UNCHANGED)
N5_img = cv2.imread("images/5.png", cv2.IMREAD_UNCHANGED)
finger_images = {
    0: N0_img,
    1: N1_img,
    2: N2_img,
    3: N3_img,
    4: N4_img,
    5: N5_img
}
# Biến kiểm tra cử chỉ Thumb Up
thumb_up_detected = False
thumb_down_detected = False
# Biến kiểm tra cử chỉ OK
ok_gesture_detected = False
Custom_detected = False
ILoveYou_detected = False
bay_detected = False
def overlay_image(background, overlay, position=(0, 0)):
    x, y = position
    h, w = overlay.shape[:2]
    roi = background[y:y+h, x:x+w]

    # Kiểm tra nếu overlay có alpha channel (transparency)
    if overlay.shape[2] == 4:
        # Tách alpha channel và các kênh màu
        overlay_rgb = overlay[:, :, :3]
        overlay_alpha = overlay[:, :, 3:] / 255.0

        # Chèn overlay vào background sử dụng alpha blending
        background[y:y+h, x:x+w] = (overlay_rgb * overlay_alpha + roi * (1 - overlay_alpha)).astype('uint8')
    else:
        background[y:y+h, x:x+w] = overlay
    return background

def countFingers(lmList):
    fingers = []

    # Kiểm tra ngón cái
    if lmList[tipIds[0]][1] > lmList[tipIds[0] - 1][1]:
        fingers.append(1)
    else:
        fingers.append(0)

    # Kiểm tra các ngón tay khác
    for id in range(1, 5):
        if lmList[tipIds[id]][2] < lmList[tipIds[id] - 2][2]:
            fingers.append(1)
        else:
            fingers.append(0)

    return fingers.count(1)
while True:
    if not cap.isOpened():
        print("Reconnecting to stream...")
        cap = cv2.VideoCapture(url)
        time.sleep(1)
        continue
    success, img = cap.read()

    if not success:
        print("Không thể đọc ảnh từ video stream.")
        continue  # Bỏ qua vòng lặp này và tiếp tục với vòng lặp kế tiếp

    if img is None:
        print("Lỗi: ảnh rỗng.")
        continue

    img = detector.findHands(img)
    lmList = detector.findPosition(img, draw=False)
    totalFingers = 0
    if lmList:
        if detector.is7Gesture(lmList):
            print("7!")
            if relay == 1:
                client.publish("yourtopic", 7)
                relay = 0
            bay_detected = True
            h, w, _ = img.shape
            bay_img_resized = cv2.resize(bay_img, (w // 4, h // 4))
            img = overlay_image(img, bay_img_resized, position=(50, 50))
        else:
            bay_detected = False
        if detector.isILoveYou(lmList):
            print("ILU!")
            if  relay == 0 :
                client.publish("yourtopic", 6)
                relay = 1
            ILoveYou_detected = True
            h, w, _ = img.shape
            y_img_resized = cv2.resize(y_img, (w // 4, h // 4))
            img = overlay_image(img, y_img_resized, position=(50, 50))
        else :
            ILoveYou_detected = False
            # Nhận diện cử chỉ "Thumbs Up"
        if detector.isThumbsUpGesture(lmList):
            print("Cử chỉ: Thumbs Up")
            if led_state2 == 0 :
                client.publish("yourtopic", 2)
                led_state2 = 1
            thumb_up_detected = True
            h, w, _ = img.shape
            like_img_resized = cv2.resize(like_img, (w // 4, h // 4))
            img = overlay_image(img, like_img_resized, position=(50, 50))
        else:
            # Nếu không phải "Thumbs Up", kiểm tra các cử chỉ khác
            thumb_up_detected = False  # Reset khi bỏ "Thumbs Up"
        if detector.isThumbsDownGesture(lmList) :
            print("Cử chỉ: Thumbs down")
            if led_state2 == 1 :
                client.publish("yourtopic", 3)
                led_state2 = 0
            thumb_down_detected = True
            h, w, _ = img.shape
            dislike_img_resized = cv2.resize(dislike_img, (w // 4, h // 4))
            img = overlay_image(img, dislike_img_resized, position=(50, 50))
        else:
            thumb_down_detected = False
        if detector.isOKGesture(lmList):
            print("Cử chỉ: OK")
            client.publish("yourtopic", 4)
            if led_state1 == 0:
                led_state1 = 1
            if led_state2 == 0:
                led_state2 = 1
            if relay == 0:
                relay = 1
            ok_gesture_detected = True  # Đánh dấu đã nhận diện "OK"
            h, w, _ = img.shape
            ok_img_resized = cv2.resize(ok_img, (w // 4, h // 4))
            img = overlay_image(img, ok_img_resized, position=(50, 50))
        else:
            ok_gesture_detected = False  # Reset khi bỏ "OK"

        if detector.isCustomGesture(lmList):
            print("Cử chỉ: Custom Gesture ")
            client.publish("yourtopic", 5)
            if led_state1 == 1:
                led_state1 = 0
            if led_state2 == 1:
                led_state2 = 0
            if relay == 1:
                relay = 0
            Custom_detected = True
            h, w, _ = img.shape
            ilu_img_resized = cv2.resize(ilu_img, (w // 4, h // 4))
            img = overlay_image(img, ilu_img_resized, position=(50, 50))
        else:
            Custom_detected = False


        if not thumb_up_detected and not ok_gesture_detected and not thumb_down_detected and not Custom_detected and not ILoveYou_detected and not bay_detected: # Chỉ đếm số ngón tay khi không phải là Thumbs Up va ok
                totalFingers = countFingers(lmList)
                print(totalFingers)
                if totalFingers in finger_images:
                    finger_img = finger_images[totalFingers]
                    h, w, _ = img.shape
                    finger_img_resized = cv2.resize(finger_img, (w // 4, h // 4))
                    img = overlay_image(img, finger_img_resized, position=(50, 50))
        # Nếu nâng 5 ngón tay
        if totalFingers == 5 and led_state1 == 0:
            client.publish("yourtopic", 1)
            led_state1 = 1  # Cập nhật trạng thái LED

        # Nếu nâng 4 ngón tay (tắt LED)
        elif totalFingers == 4 and led_state1 == 1:
            client.publish("yourtopic", 0)
            led_state1 = 0  # Cập nhật trạng thái LED
    cv2.imshow("Image", img)
    cv2.waitKey(1)
