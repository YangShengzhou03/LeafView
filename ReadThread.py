from PyQt6 import QtWidgets, QtCore, QtGui
import dlib
import numpy as np
import os


class FaceSystem(QtCore.QObject):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.face_detector = dlib.get_frontal_face_detector()
        self.face_encoder = dlib.face_recognition_model_v1("dlib_face_recognition_resnet_model_v1.dat")
        self.shape_predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        self.face_groups = {}

        # Connect UI signals
        self.parent.toolButton_back.clicked.connect(self.navigate_back)
        self.parent.scrollArea_people.mouseDoubleClickEvent = self.handle_double_click

    def load_faces(self, directory):
        """Load and group faces from directory"""
        self.face_groups.clear()

        # Clear existing widgets
        while self.parent.gridLayout_7.count():
            item = self.parent.gridLayout_7.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Process images
        for filename in os.listdir(directory):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                path = os.path.join(directory, filename)
                self.process_image(path)

        # Display grouped faces
        self.display_face_groups()

    def process_image(self, image_path):
        """Detect and encode faces in an image"""
        img = dlib.load_rgb_image(image_path)
        faces = self.face_detector(img)

        for face in faces:
            shape = self.shape_predictor(img, face)
            face_descriptor = np.array(self.face_encoder.compute_face_descriptor(img, shape))

            # Find matching group
            group_id = self.find_matching_group(face_descriptor)

            if group_id not in self.face_groups:
                self.face_groups[group_id] = {
                    'descriptor': face_descriptor,
                    'images': []
                }

            # Store face data
            self.face_groups[group_id]['images'].append({
                'path': image_path,
                'rect': (face.left(), face.top(), face.width(), face.height())
            })

    def find_matching_group(self, descriptor, threshold=0.6):
        """Find existing face group or create new one"""
        for group_id, group in self.face_groups.items():
            dist = np.linalg.norm(descriptor - group['descriptor'])
            if dist < threshold:
                return group_id
        return len(self.face_groups)  # New group ID

    def display_face_groups(self):
        """Show face groups in grid layout"""
        row, col = 0, 0
        max_cols = 4

        for group_id, group in self.face_groups.items():
            if group['images']:
                # Create face group widget
                face_widget = FaceGroupWidget(group['images']['path'],
                                              f"Person {group_id + 1}",
                                              len(group['images']),
                                              self.parent)

                # Connect double click signal
                face_widget.doubleClicked.connect(lambda _, gid=group_id: self.show_group_images(gid))

                # Add to grid
                self.parent.gridLayout_7.addWidget(face_widget, row, col)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

    def show_group_images(self, group_id):
        """Show all images for a specific group"""
        # Clear previous images
        while self.parent.verticalLayout_7.count():
            item = self.parent.verticalLayout_7.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add back button at top
        self.parent.verticalLayout_7.addWidget(self.parent.toolButton_back)

        # Create scroll area for images
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        layout = QtWidgets.QFlowLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Add all images from group
        for img_data in self.face_groups[group_id]['images']:
            face_img = FaceImageWidget(img_data['path'], img_data['rect'])
            layout.addWidget(face_img)

        scroll.setWidget(content)
        self.parent.verticalLayout_7.addWidget(scroll)

        # Switch to image view
        self.parent.stackedWidget_face.setCurrentWidget(self.parent.page_people_image)

    def navigate_back(self):
        """Return to face groups view"""
        self.parent.stackedWidget_face.setCurrentWidget(self.parent.page_people)

    def handle_double_click(self, event):
        """Handle double click on empty space"""
        if not self.parent.gridLayout_7.itemAtPosition(0, 0):
            self.load_faces("default_faces_directory")
        QtWidgets.QScrollArea.mouseDoubleClickEvent(self.parent.scrollArea_people, event)


class FaceGroupWidget(QtWidgets.QFrame):
    doubleClicked = QtCore.pyqtSignal(int)

    def __init__(self, image_path, name, count, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 190)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setup_ui(image_path, name, count)

    def setup_ui(self, image_path, name, count):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Image container with shadow
        img_container = QtWidgets.QFrame()
        img_container.setFixedSize(140, 140)
        img_container.setStyleSheet("background: white; border-radius: 8px;")

        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QtGui.QColor(0, 0, 0, 30))
        img_container.setGraphicsEffect(shadow)

        # Face image
        img_label = QtWidgets.QLabel()
        img_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        img_label.setFixedSize(120, 120)

        # Load and crop face
        pixmap = QtGui.QPixmap(image_path)
        if not pixmap.isNull():
            # Simple crop (real implementation should use face rect)
            cropped = pixmap.scaled(120, 120,
                                    QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                    QtCore.Qt.TransformationMode.SmoothTransformation)
            img_label.setPixmap(cropped)

        # Add to container
        img_layout = QtWidgets.QVBoxLayout(img_container)
        img_layout.addWidget(img_label)

        # Text labels
        name_label = QtWidgets.QLabel(name)
        name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-weight: bold; font-size: 12pt;")

        count_label = QtWidgets.QLabel(f"{count} images")
        count_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        count_label.setStyleSheet("color: #666; font-size: 10pt;")

        # Assemble layout
        layout.addWidget(img_container)
        layout.addWidget(name_label)
        layout.addWidget(count_label)

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit(0)  # Group ID will be set in lambda


class FaceImageWidget(QtWidgets.QFrame):
    def __init__(self, image_path, face_rect, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 220)
        self.setup_ui(image_path, face_rect)

    def setup_ui(self, image_path, face_rect):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Load and crop face
        pixmap = QtGui.QPixmap(image_path)
        if not pixmap.isNull():
            # Crop to face rectangle
            cropped = pixmap.copy(*face_rect)
            cropped = cropped.scaled(170, 170,
                                     QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                     QtCore.Qt.TransformationMode.SmoothTransformation)

            img_label = QtWidgets.QLabel()
            img_label.setPixmap(cropped)
            img_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            layout.addWidget(img_label)

        # Add filename label
        name = os.path.basename(image_path)
        name_label = QtWidgets.QLabel(name)
        name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)

        layout.addWidget(name_label)
