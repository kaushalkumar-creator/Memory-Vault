[app]
title = Memory Vault
package.name = memoryvault
package.domain = org.memoryvault
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
source.exclude_dirs = .github, bin, .buildozer
version = 0.2.0
requirements = python3,kivy==2.3.1,sqlite3
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES
android.api = 36
android.minapi = 24
android.ndk = 29
p4a.branch = develop
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
