MediaPipe Face Mesh
Overview
MediaPipe Face Mesh is a face geometry solution that estimates 468 3D face landmarks in real-time even on mobile devices. It employs machine learning (ML) to infer the 3D surface geometry, requiring only a single camera input without the need for a dedicated depth sensor. Utilizing lightweight model architectures together with GPU acceleration throughout the pipeline, the solution delivers real-time performance critical for live experiences.

Additionally, the solution is bundled with the Face Geometry module that bridges the gap between the face landmark estimation and useful real-time augmented reality (AR) applications. It establishes a metric 3D space and uses the face landmark screen positions to estimate face geometry within that space. The face geometry data consists of common 3D geometry primitives, including a face pose transformation matrix and a triangular face mesh. Under the hood, a lightweight statistical analysis method called Procrustes Analysis is employed to drive a robust, performant and portable logic. The analysis runs on CPU and has a minimal speed/memory footprint on top of the ML model inference.


Fig 1. AR effects utilizing facial surface geometry.
ML Pipeline
Our ML pipeline consists of two real-time deep neural network models that work together: A detector that operates on the full image and computes face locations and a 3D face landmark model that operates on those locations and predicts the approximate surface geometry via regression. Having the face accurately cropped drastically reduces the need for common data augmentations like affine transformations consisting of rotations, translation and scale changes. Instead it allows the network to dedicate most of its capacity towards coordinate prediction accuracy. In addition, in our pipeline the crops can also be generated based on the face landmarks identified in the previous frame, and only when the landmark model could no longer identify face presence is the face detector invoked to relocalize the face. This strategy is similar to that employed in our MediaPipe Hands solution, which uses a palm detector together with a hand landmark model.

The pipeline is implemented as a MediaPipe graph that uses a face landmark subgraph from the face landmark module, and renders using a dedicated face renderer subgraph. The face landmark subgraph internally uses a face_detection_subgraph from the face detection module.

Note: To visualize a graph, copy the graph and paste it into MediaPipe Visualizer. For more information on how to visualize its associated subgraphs, please see visualizer documentation.

Models
Face Detection Model
The face detector is the same BlazeFace model used in MediaPipe Face Detection. Please refer to MediaPipe Face Detection for details.

Face Landmark Model
For 3D face landmarks we employed transfer learning and trained a network with several objectives: the network simultaneously predicts 3D landmark coordinates on synthetic rendered data and 2D semantic contours on annotated real-world data. The resulting network provided us with reasonable 3D landmark predictions not just on synthetic but also on real-world data.

The 3D landmark network receives as input a cropped video frame without additional depth input. The model outputs the positions of the 3D points, as well as the probability of a face being present and reasonably aligned in the input. A common alternative approach is to predict a 2D heatmap for each landmark, but it is not amenable to depth prediction and has high computational costs for so many points. We further improve the accuracy and robustness of our model by iteratively bootstrapping and refining predictions. That way we can grow our dataset to increasingly challenging cases, such as grimaces, oblique angle and occlusions.

You can find more information about the face landmark model in this paper.


Fig 2. Face landmarks: the red box indicates the cropped area as input to the landmark model, the red dots represent the 468 landmarks in 3D, and the green lines connecting landmarks illustrate the contours around the eyes, eyebrows, lips and the entire face.
Face Geometry Module
The Face Landmark Model performs a single-camera face landmark detection in the screen coordinate space: the X- and Y- coordinates are normalized screen coordinates, while the Z coordinate is relative and is scaled as the X coodinate under the weak perspective projection camera model. This format is well-suited for some applications, however it does not directly enable the full spectrum of augmented reality (AR) features like aligning a virtual 3D object with a detected face.

The Face Geometry module moves away from the screen coordinate space towards a metric 3D space and provides necessary primitives to handle a detected face as a regular 3D object. By design, you'll be able to use a perspective camera to project the final 3D scene back into the screen coordinate space with a guarantee that the face landmark positions are not changed.

Key Concepts
Metric 3D Space
The Metric 3D space established within the Face Geometry module is a right-handed orthonormal metric 3D coordinate space. Within the space, there is a virtual perspective camera located at the space origin and pointed in the negative direction of the Z-axis. In the current pipeline, it is assumed that the input camera frames are observed by exactly this virtual camera and therefore its parameters are later used to convert the screen landmark coordinates back into the Metric 3D space. The virtual camera parameters can be set freely, however for better results it is advised to set them as close to the real physical camera parameters as possible.


Fig 3. A visualization of multiple key elements in the Metric 3D space.
Canonical Face Model
The Canonical Face Model is a static 3D model of a human face, which follows the 468 3D face landmark topology of the Face Landmark Model. The model bears two important functions:

Defines metric units: the scale of the canonical face model defines the metric units of the Metric 3D space. A metric unit used by the default canonical face model is a centimeter;
Bridges static and runtime spaces: the face pose transformation matrix is - in fact - a linear map from the canonical face model into the runtime face landmark set estimated on each frame. This way, virtual 3D assets modeled around the canonical face model can be aligned with a tracked face by applying the face pose transformation matrix to them.
Components
Geometry Pipeline
The Geometry Pipeline is a key component, which is responsible for estimating face geometry objects within the Metric 3D space. On each frame, the following steps are executed in the given order:

Face landmark screen coordinates are converted into the Metric 3D space coordinates;
Face pose transformation matrix is estimated as a rigid linear mapping from the canonical face metric landmark set into the runtime face metric landmark set in a way that minimizes a difference between the two;
A face mesh is created using the runtime face metric landmarks as the vertex positions (XYZ), while both the vertex texture coordinates (UV) and the triangular topology are inherited from the canonical face model.
The geometry pipeline is implemented as a MediaPipe calculator. For your convenience, the face geometry pipeline calculator is bundled together with the face landmark module into a unified MediaPipe subgraph. The face geometry format is defined as a Protocol Buffer message.

Effect Renderer
The Effect Renderer is a component, which serves as a working example of a face effect renderer. It targets the OpenGL ES 2.0 API to enable a real-time performance on mobile devices and supports the following rendering modes:

3D object rendering mode: a virtual object is aligned with a detected face to emulate an object attached to the face (example: glasses);
Face mesh rendering mode: a texture is stretched on top of the face mesh surface to emulate a face painting technique.
In both rendering modes, the face mesh is first rendered as an occluder straight into the depth buffer. This step helps to create a more believable effect via hiding invisible elements behind the face surface.

The effect renderer is implemented as a MediaPipe calculator.


Fig 4. An example of face effects rendered by the Face Geometry Effect Renderer.
Example Apps
Please first see general instructions for Android, iOS and desktop on how to build MediaPipe examples.

Note: To visualize a graph, copy the graph and paste it into MediaPipe Visualizer. For more information on how to visualize its associated subgraphs, please see visualizer documentation.

Face Landmark Example
Face landmark example showcases real-time, cross-platform face landmark detection. For visual reference, please refer to Fig. 2.

Mobile
Graph: mediapipe/graphs/face_mesh/face_mesh_mobile.pbtxt
Android target: (or download prebuilt ARM64 APK) mediapipe/examples/android/src/java/com/google/mediapipe/apps/facemeshgpu:facemeshgpu
iOS target: mediapipe/examples/ios/facemeshgpu:FaceMeshGpuApp
Tip: Maximum number of faces to detect/process is set to 1 by default. To change it, for Android modify NUM_FACES in MainActivity.java, and for iOS modify kNumFaces in FaceMeshGpuViewController.mm.

Desktop
Running on CPU
Graph: mediapipe/graphs/face_mesh/face_mesh_desktop_live.pbtxt
Target: mediapipe/examples/desktop/face_mesh:face_mesh_cpu
Running on GPU
Graph: mediapipe/graphs/face_mesh/face_mesh_desktop_live_gpu.pbtxt
Target: mediapipe/examples/desktop/face_mesh:face_mesh_gpu
Tip: Maximum number of faces to detect/process is set to 1 by default. To change it, in the graph file modify the option of ConstantSidePacketCalculator.

Face Effect Example
Face effect example showcases real-time mobile face effect application use case for the Face Mesh solution. To enable a better user experience, this example only works for a single face. For visual reference, please refer to Fig. 4.

Mobile
Graph: mediapipe/graphs/face_effect/face_effect_gpu.pbtxt
Android target: (or download prebuilt ARM64 APK) mediapipe/examples/android/src/java/com/google/mediapipe/apps/faceeffect
iOS target: mediapipe/examples/ios/faceeffect

Face Landmarker task

The MediaPipe Face Landmarker task lets you detect face landmarks and facial expressions in images and videos. You can use this task to identify human facial expressions, apply facial filters and effects, and create virtual avatars. This task uses machine learning (ML) models that can work with single images or a continuous stream of images. The task outputs 3-dimensional face landmarks, blendshape scores (coefficients representing facial expression) to infer detailed facial surfaces in real-time, and transformation matrices to perform the transformations required for effects rendering.

Try it!arrow_forward

Get Started
Start using this task by following one of the implementation guides for your target platform. These platform-specific guides walk you through a basic implementation of this task, including a recommended model, and code example with recommended configuration options:

Android - Code example - Guide
Python - Code example - Guide
Web - Code example - Guide
Task details
This section describes the capabilities, inputs, outputs, and configuration options of this task.

Features
Input image processing - Processing includes image rotation, resizing, normalization, and color space conversion.
Score threshold - Filter results based on prediction scores.
Task inputs	Task outputs
The Face Landmarker accepts an input of one of the following data types:
Still images
Decoded video frames
Live video feed
The Face Landmarker outputs the following results:
A complete face mesh for each detected face, with blendshape scores denoting facial expressions and coordinates for facial landmarks.
Face Blendshape and Facial transformation matrixes
Configurations options
This task has the following configuration options:

Option Name	Description	Value Range	Default Value
running_mode	Sets the running mode for the task. There are three modes:

IMAGE: The mode for single image inputs.

VIDEO: The mode for decoded frames of a video.

LIVE_STREAM: The mode for a livestream of input data, such as from a camera. In this mode, resultListener must be called to set up a listener to receive results asynchronously.	{IMAGE, VIDEO, LIVE_STREAM}	IMAGE
num_faces	The maximum number of faces that can be detected by the the FaceLandmarker. Smoothing is only applied when num_faces is set to 1.	Integer > 0	1
min_face_detection_confidence	The minimum confidence score for the face detection to be considered successful.	Float [0.0,1.0]	0.5
min_face_presence_confidence	The minimum confidence score of face presence score in the face landmark detection.	Float [0.0,1.0]	0.5
min_tracking_confidence	The minimum confidence score for the face tracking to be considered successful.	Float [0.0,1.0]	0.5
output_face_blendshapes	Whether Face Landmarker outputs face blendshapes. Face blendshapes are used for rendering the 3D face model.	Boolean	False
output_facial_transformation_matrixes	Whether FaceLandmarker outputs the facial transformation matrix. FaceLandmarker uses the matrix to transform the face landmarks from a canonical face model to the detected face, so users can apply effects on the detected landmarks.	Boolean	False
result_callback	Sets the result listener to receive the landmarker results asynchronously when FaceLandmarker is in the live stream mode. Can only be used when running mode is set to LIVE_STREAM	ResultListener	N/A
Models
The Face Landmarker uses a series of models to predict face landmarks. The first model detects faces, a second model locates landmarks on the detected faces, and a third model uses those landmarks to identify facial features and expressions.

The following models are packaged together into a downloadable model bundle:

Face detection model: detects the presence of faces with a few key facial landmarks.
Face mesh model: adds a complete mapping of the face. The model outputs an estimate of 478 3-dimensional face landmarks.
Blendshape prediction model: receives output from the face mesh model predicts 52 blendshape scores, which are coefficients representing facial different expressions.
The face detection model is the BlazeFace short-range model, a lightweight and accurate face detector optimized for mobile GPU inference. For more information, see the Face Detector task.

The image below shows a complete mapping of facial landmarks from the model bundle output.

Face Landmarker keypoints

For a more detailed view of the face landmarks, see the full-size image.

Attention: This MediaPipe Solutions Preview is an early release. Learn more.
Model bundle	Input shape	Data type	Model Cards	Versions
FaceLandmarker	FaceDetector: 192 x 192
FaceMesh-V2: 256 x 256
Blendshape: 1 x 146 x 2	float 16	FaceDetector
FaceMesh-V2
Blendshape