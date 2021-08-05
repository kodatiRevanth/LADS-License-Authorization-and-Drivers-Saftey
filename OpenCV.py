from scipy.spatial import distance as dist
from imutils import face_utils
import cv2
import face_recognition
import numpy as np
import pickle
import dlib
import imutils
import os
import scipy.misc
from imutils import paths
import pyzbar.pyzbar as pyzbar

#==================================================OPEN-CV==============================================================#
class VideoCapture:
    def __init__(self, video_source=0):
        self.vid = cv2.VideoCapture(video_source + cv2.CAP_DSHOW)
        self.scale_factor = 0.5
        if not self.vid.isOpened():
            raise ValueError("unable to open this camera \n select another video source", video_source)
        self.flag = False
        self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.decision = []
        self.decodeObjects = []
        self.authorize = True
        self.EYE_AR_THRESH = 0.3
        self.EYE_AR_CONSEC_FRAMES = 48
        self.COUNTER = 0
        self.ALARM_ON = False
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')
        (self.lStart, self.lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
        (self.rStart, self.rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
        self.qr_data = ''


    def getFrame(self):
        if self.vid.isOpened():
            isTrue, frame = self.vid.read()
            if isTrue:
                return (isTrue, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            else:
                return (isTrue, None)

    #Recognition
    def recognize(self):
        with open ('test_encodes.dat', 'rb') as fp:
            data = pickle.load(fp)
        known_face_encodings = data["encodings"]
        known_face_names = data["names"]
        face_locations = []
        face_encodings = []
        face_names = []
        process_this_frame = True
        i = 0
        scale_factor = 0.5
        if self.vid.isOpened():
            while len(self.decision) < 5:
                isTrue, frame = self.vid.read()
                if isTrue:
                    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)  # , fx=0.25, fy=0.25
                    rgb_small_frame = small_frame[:, :, ::-1]
                    i = i + 1
                    if process_this_frame:
                        face_locations = face_recognition.face_locations(rgb_small_frame)
                        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                        face_names = []
                        for face_encoding in face_encodings:
                            name = VideoCapture.find_match(known_face_encodings, known_face_names,
                                                           face_encodings[0])
                            face_names.append(name)

                    process_this_frame = not process_this_frame
                    for (x, y, w, h), name in zip(face_locations, face_names):  # Rescaling
                        x *= 4
                        y *= 4
                        w *= 4
                        h *= 4

                        cv2.rectangle(frame, (h, x), (y, w), (235, 206, 135), 2)
                        cv2.rectangle(frame, (h, w - 35), (y, w), (235, 206, 135), cv2.FILLED)
                        font = cv2.FONT_HERSHEY_DUPLEX
                        cv2.putText(frame, name, (h + 6, w - 6), font, 1.0, (0, 0, 0), 1)
                        self.decision.append(name)
                    return (isTrue, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), False)
                else:
                    return (isTrue, None, False)
            i = 0
            for elem in self.decision:
                if self.decision.count(elem) >= 3 and self.decision[i] == 'Not Found':
                    self.authorize = False
            self.decision= []
            return True, None, True


    def find_match(known_faces, names, face):
        scale_factor=0.5
        matches = face_recognition.compare_faces(known_faces, face)
        face_distances = face_recognition.face_distance(known_faces, face)
        best_match_index = np.argmin(face_distances)

        if matches[best_match_index]:
            if(face_distances[best_match_index]<scale_factor):
                name = names[best_match_index]
                return(name)
        return 'Not Found'
    #Recognition End

    #EAR
    def ear(self):
        if self.vid.isOpened():
            isTrue, frame = self.vid.read()
            if isTrue:
                #frame = imutils.resize(frame, width=450)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                rects = self.detector(gray, 0)
                for rect in rects:
                    shape = self.predictor(gray, rect)
                    shape = face_utils.shape_to_np(shape)
                    leftEye = shape[self.lStart:self.lEnd]
                    rightEye = shape[self.rStart:self.rEnd]
                    leftEAR = self.eye_aspect_ratio(leftEye)
                    rightEAR = self.eye_aspect_ratio(rightEye)
                    ear = (leftEAR + rightEAR) / 2.0
                    leftEyeHull = cv2.convexHull(leftEye)
                    rightEyeHull = cv2.convexHull(rightEye)
                    cv2.drawContours(frame, [leftEyeHull], -1, (255, 255, 255), 1)
                    cv2.drawContours(frame, [rightEyeHull], -1, (255, 255, 255), 1)
                    if ear < self.EYE_AR_THRESH:
                        self.COUNTER += 1
                        if self.COUNTER >= self.EYE_AR_CONSEC_FRAMES:
                            if not self.ALARM_ON:
                                self.ALARM_ON = True
                                #Run adminsleepy.py

                            cv2.putText(frame, "DROWSINESS ALERT!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    else:
                        self.COUNTER = 0
                        ALARM_ON = False
                    cv2.putText(frame, "EAR: {:.2f}".format(ear), (500, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                return (isTrue, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            else:
                return (isTrue, None)

    def eye_aspect_ratio(self,eye):
        # compute the euclidean distances between the two sets of
        # vertical eye landmarks (x, y)-coordinates
        A = dist.euclidean(eye[1], eye[5])
        B = dist.euclidean(eye[2], eye[4])

        # compute the euclidean distance between the horizontal
        # eye landmark (x, y)-coordinates
        C = dist.euclidean(eye[0], eye[3])

        # compute the eye aspect ratio
        ear = (A + B) / (2.0 * C)

        # return the eye aspect ratio
        return ear
    #EAR End

    #Storing Images
    def storingImages(self, name, unknown=False):
        self.name = name
        self.unkown = unknown
        face_cascade = cv2.CascadeClassifier('Haar/haarcascade_frontalcatface.xml')
        Count = 0
        if not self.unkown:
            path = "images/" + self.name
        else:
            path = "unknown/" + self.name
        os.mkdir(path)
        if self.vid.isOpened():
            isTrue, frame = self.vid.read()
            if isTrue:
                while Count < 4:
                    faces = face_cascade.detectMultiScale(frame, 1.3, 5)
                    for (x, y, w, h) in faces:
                        cv2.waitKey(500)
                        print(path + '/' + str(Count) + ".jpg")
                        cv2.imwrite(path + '/' + str(Count) + ".jpg", frame)
                        Count = Count + 1
    #Storing Images end

    #Training Images
    def trainingImages(self):
        self.face_recognition_model = dlib.face_recognition_model_v1('Face_Recognition_trainedData.dat')
        self.TOLERANCE = 0.5

        self.paths_to_images = list(paths.list_images('images'))
        print(self.paths_to_images)
        self.face_encodings = []
        self.face_names = []
        for (i, self.path_to_image) in enumerate(self.paths_to_images):
            name = self.path_to_image.split(os.path.sep)[-2]
            self.face_encodings_in_image = self.get_face_encodings()
            self.face_encodings.append(self.face_encodings_in_image[0])
            self.face_names.append(name)

        self.data = {"encodings": self.face_encodings, "names": self.face_names}
        with open('test_encodes.dat', 'wb') as fp:
            pickle.dump(self.data, fp)
        print("Finshed Training")

    def get_face_encodings(self):
        self.image = scipy.misc.imread(self.path_to_image)
        self.detected_faces = self.detector(self.image, 1)
        self.shapes_faces = [self.predictor(self.image, face) for face in self.detected_faces]
        return [np.array(self.face_recognition_model.compute_face_descriptor(self.image, face_pose, 1)) for face_pose in
                self.shapes_faces]
    # Training Images end

    #Detect QR
    def getQR(self, lic):
        self.lic = lic
        if self.vid.isOpened():
            while len(self.decodeObjects) < 1:
                isTrue, frame = self.vid.read()
                if isTrue:
                    self.decodeObjects = pyzbar.decode(frame)
                    for obj in self.decodeObjects:
                        self.qr_data += str(obj.data)
                        cv2.putText(frame, str(obj.data), (50, 50), cv2.FONT_HERSHEY_PLAIN, 2,(255, 0, 0), 3)
                    return isTrue, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), False
                else:
                    return isTrue, None, False
        self.qr_data = self.qr_data[2:-1]
        self.decodeObjects = []
        if self.qr_data == self.lic:
            return False, None, True
        else:
            return False, None, False

    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()