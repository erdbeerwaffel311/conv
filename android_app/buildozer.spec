[app]

# (str) Title of your application
title = Universal Media Converter

# (str) Package name
package.name = universalmediaconverter

# (str) Package domain (needed for android/ios packaging)
package.domain = com.elias

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json

# (str) Application versioning (method 1)
version = 2.1.1

# (list) Application requirements
# Comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,pillow,pypdf,openpyxl,yt-dlp,certifi

# (str) Presplash of the application
presplash.filename = %(source.dir)s/icon.png

# (str) Icon of the application
icon.filename = %(source.dir)s/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_AUDIO,READ_MEDIA_VIDEO,READ_MEDIA_IMAGES

# (int) Target Android API, should be as high as possible.
# (int) Target Android API
android.api = 33

# (int) Minimum API your APK will support
android.minapi = 24

# (str) Android NDK version to use - r25b is the stable standard for python-for-android
android.ndk = 25b

# (bool) Automatically accept SDK license
android.accept_sdk_license = True

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (list) The Android archs to build for (Samsung Galaxy A55 5G is 64-bit ARM)
android.archs = arm64-v8a

# (list) Android native libraries to bundle into APK for arm64-v8a
android.add_libs_arm64_v8a = libs/arm64-v8a/*.so

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) The format used to package the app for release mode (aab or apk)
android.release_artifact = apk

# (str) python-for-android git clone directory
p4a.source_dir = ../p4a_dir

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
