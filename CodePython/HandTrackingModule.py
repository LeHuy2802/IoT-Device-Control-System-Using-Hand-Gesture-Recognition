
import cv2
import mediapipe as mp
import time
import math
class handDetector():
    def __init__(self, mode=False, maxHands=2, detectionCon=0.5, trackCon=0.5):
        self.mode = mode
        self.maxHands = maxHands
        self.detectionCon = detectionCon
        self.trackCon = trackCon

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(self.mode, self.maxHands,
                                        self.detectionCon, self.trackCon)
        self.mpDraw = mp.solutions.drawing_utils

    def findHands(self, img, draw=True):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)
        # print(results.multi_hand_landmarks)

        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                if draw:
                    self.mpDraw.draw_landmarks(img, handLms,
                                               self.mpHands.HAND_CONNECTIONS)
        return img

    def findPosition(self, img, handNo=0, draw=True):

        lmList = []
        if self.results.multi_hand_landmarks:
            myHand = self.results.multi_hand_landmarks[handNo]
            for id, lm in enumerate(myHand.landmark):
                # print(id, lm)
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                # print(id, cx, cy)
                lmList.append([id, cx, cy])
                if draw:
                    cv2.circle(img, (cx, cy), 15, (255, 0, 255), cv2.FILLED)

        return lmList

    def isOKGesture(self, lmList, threshold=30):
        if len(lmList) == 0:
            return False

        # Tính khoảng cách giữa đầu ngón cái và ngón trỏ
        thumb_tip = lmList[4]
        index_tip = lmList[8]
        distance = ((thumb_tip[1] - index_tip[1]) ** 2 + (thumb_tip[2] - index_tip[2]) ** 2) ** 0.5

        # Kiểm tra nếu khoảng cách giữa ngón cái và ngón trỏ nhỏ hơn ngưỡng (cử chỉ OK)
        is_thumb_index_close = distance < 60  # Ngưỡng khoảng cách

        # Kiểm tra ba ngón giữa, áp út và út phải cao hơn khớp dưới của chúng một khoảng cách nhất định
        is_middle_straight = (lmList[12][2] < lmList[11][2] - threshold)  # Ngón giữa cao hơn khớp PIP
        is_ring_straight = (lmList[16][2] < lmList[14][2] - threshold)  # Ngón áp út cao hơn khớp PIP
        is_pinky_straight = (lmList[20][2] < lmList[18][2] - threshold)  # Ngón út cao hơn khớp PIP

        # Kiểm tra tất cả các ngón giữa, áp út, út phải cao hơn khớp dưới một khoảng cách nhất định
        is_other_fingers_straight = is_middle_straight and is_ring_straight and is_pinky_straight

        return is_thumb_index_close and is_other_fingers_straight

    def isThumbsUpGesture(self, lmList):
        if len(lmList) == 0:
            return False

        # Kiểm tra ngón cái: đầu ngón cái phải cao hơn khớp dưới của nó (IP)
        is_thumb_up = lmList[4][2] < lmList[3][2]

        # Kiểm tra ngón cái phải giơ lên, không bị chạm với các ngón khác
        for tip in [8, 12, 16, 20]:  # Kiểm tra các ngón tay còn lại (trừ ngón cái)
            if lmList[4][2] >= lmList[tip - 2][2]:  # Nếu đầu ngón cái không cao hơn khớp dưới của các ngón tay khác
                is_thumb_up = False
                break

        # Kiểm tra các ngón tay còn lại phải gập xuống (không duỗi thẳng)
        is_other_fingers_folded = all(
            lmList[tip][2] > lmList[tip - 2][2] or lmList[tip][1] < lmList[tip - 3][1]
            for tip in [8, 12, 16, 20]  # Kiểm tra ngón trỏ, giữa, áp út và út
        )

        # Kiểm tra các ngón tay còn lại phải gập xuống và không có ngón nào duỗi ra
        is_no_fingers_straight = all(
            lmList[tip][2] > lmList[tip - 2][2]  # Kiểm tra các ngón tay gập xuống
            for tip in [8, 12, 16, 20]
        )

        # Trả về True nếu ngón cái giơ lên và các ngón tay còn lại gập xuống
        return is_thumb_up and is_other_fingers_folded and is_no_fingers_straight

    def isThumbsDownGesture(self, lmList):
        if len(lmList) == 0:
            return False

        # Kiểm tra ngón cái: đầu ngón cái phải thấp hơn khớp dưới của nó (MCP)
        thumb_tip_y = lmList[4][2]  # Đầu ngón cái
        thumb_mcp_y = lmList[3][2]  # Khớp MCP ngón cái

        # Điều kiện ngón cái phải thấp hơn một ngưỡng lớn hơn so với hiện tại
        is_thumb_down = thumb_tip_y > thumb_mcp_y + 30  # Giả sử ngón cái phải thấp hơn ít nhất 10 đơn vị (tùy chỉnh theo yêu cầu)

        # Kiểm tra các ngón còn lại: các ngón tay còn lại phải gập xuống
        is_other_fingers_folded = all(
            lmList[tip][2] > lmList[tip - 2][2] or lmList[tip][1] < lmList[tip - 3][1]
            for tip in [8, 12, 16, 20]
        )

        # Trả về True nếu ngón cái chỉ xuống (với điều kiện mới) và các ngón tay còn lại gập xuống
        return is_thumb_down and is_other_fingers_folded

    def isCustomGesture(self, lmList):
        if len(lmList) == 0:
            return False

        # Kiểm tra ngón cái phải giơ lên
        is_thumb_up = lmList[4][2] < lmList[3][2] and lmList[4][2] < lmList[12][2] and lmList[4][2] < lmList[16][2]

        # Kiểm tra ngón trỏ phải giơ lên
        is_index_up = lmList[8][2] < lmList[6][2]

        # Kiểm tra ngón giữa phải gập lại
        is_middle_bent = lmList[12][2] > lmList[10][2]

        # Kiểm tra ngón áp út phải gập lại
        is_ring_bent = lmList[16][2] > lmList[14][2]

        # Kiểm tra ngón út phải giơ lên
        is_pinky_up = lmList[20][2] < lmList[18][2]

        # Cả 5 điều kiện đều phải đúng
        return is_thumb_up and is_index_up and is_pinky_up and is_middle_bent and is_ring_bent

    def isILoveYou(self, lmList):
        if len(lmList) == 0:
            return False

        # Lấy tọa độ các ngón tay
        thumb_tip = lmList[4]  # Đầu ngón cái
        thumb_ip = lmList[3]  # Khớp IP ngón cái
        pinky_tip = lmList[20]  # Đầu ngón út
        pinky_mcp = lmList[17]  # Khớp MCP ngón út
        index_tip = lmList[8]  # Đầu ngón trỏ
        middle_tip = lmList[12]  # Đầu ngón giữa
        ring_tip = lmList[16]  # Đầu ngón áp út

        # Các khớp PIP của các ngón tay gập xuống
        index_pip = lmList[6]  # Khớp PIP ngón trỏ
        middle_pip = lmList[10]  # Khớp PIP ngón giữa
        ring_pip = lmList[14]  # Khớp PIP ngón áp út

        # Điều kiện 1: Ngón cái phải duỗi thẳng
        is_thumb_straight = thumb_tip[1] > thumb_ip[1]  # Ngón cái duỗi thẳng

        # Điều kiện 2: Ngón út phải giơ lên (đầu ngón út trên cao hơn khớp MCP)
        is_pinky_straight = pinky_tip[2] < pinky_mcp[2]  # Ngón út giơ lên

        # Điều kiện 3: Các ngón trỏ, giữa và áp út phải gập xuống
        is_index_folded = index_tip[2] > index_pip[2]  # Ngón trỏ gập
        is_middle_folded = middle_tip[2] > middle_pip[2]  # Ngón giữa gập
        is_ring_folded = ring_tip[2] > ring_pip[2]  # Ngón áp út gập

        # Điều kiện 4: Ngón cái và ngón út không quá gần nhau
        is_thumb_pinky_distance_ok = abs(thumb_tip[1] - pinky_tip[1]) > 30

        # Điều kiện 5: Đầu ngón út phải cao hơn khớp PIP của các ngón tay gập xuống ít nhất 40 pixel (4 cm)
        min_pip_height = min(index_pip[2], middle_pip[2], ring_pip[2])  # Tìm chiều cao thấp nhất của các khớp PIP
        is_pinky_raised_above_pip = pinky_tip[
                                        2] < min_pip_height - 43  # Đầu ngón út phải cao hơn khớp PIP ít nhất 40 pixel (4 cm)

        # Kết hợp tất cả các điều kiện
        return (is_thumb_straight and is_pinky_straight and
                is_index_folded and is_middle_folded and
                is_ring_folded and is_thumb_pinky_distance_ok and
                is_pinky_raised_above_pip)

    def is7Gesture(self, lmList, threshold=30):
        if len(lmList) == 0:
            return False

        # Tính khoảng cách giữa đầu ngón cái và ngón áp út
        thumb_tip = lmList[4]  # Đầu ngón cái
        ring_tip = lmList[16]  # Đầu ngón áp út
        distance = ((thumb_tip[1] - ring_tip[1]) ** 2 + (thumb_tip[2] - ring_tip[2]) ** 2) ** 0.5

        # Kiểm tra nếu khoảng cách giữa ngón cái và ngón áp út nhỏ hơn ngưỡng (cử chỉ OK)
        is_thumb_ring_close = distance < 60  # Ngưỡng khoảng cách

        # Kiểm tra ngón trỏ, ngón giữa và ngón út phải cao hơn khớp dưới của chúng
        is_index_straight = lmList[8][2] < lmList[6][2] - threshold  # Ngón trỏ cao hơn khớp PIP
        is_middle_straight = lmList[12][2] < lmList[10][2] - threshold  # Ngón giữa cao hơn khớp PIP
        is_pinky_straight = lmList[20][2] < lmList[18][2] - threshold  # Ngón út cao hơn khớp PIP

        # Kiểm tra tất cả các ngón phải duỗi thẳng
        is_other_fingers_straight = is_index_straight and is_middle_straight and is_pinky_straight

        # Kết hợp tất cả điều kiện
        return is_thumb_ring_close and is_other_fingers_straight


def main():
    pTime = 0
    cTime = 0
    cap = cv2.VideoCapture(1)
    detector = handDetector()
    while True:
        success, img = cap.read()
        img = detector.findHands(img)
        lmList = detector.findPosition(img)
        if len(lmList) != 0:
            print(lmList[4])

        cv2.imshow("Image", img)
        cv2.waitKey(1)


if __name__ == "__main__":
    main()