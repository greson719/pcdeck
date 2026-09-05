"""
Comprehensive automated tests for PCDeck Gamepad Engine, Audio/Mic Sink, and Virtual Camera Streamer.
"""

import sys
import os
import time

# Ensure workspace root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.gamepad_manager import GamepadManager, is_vigem_installed, install_vigem_silently
from server.audio_streamer import MicrophoneSink, mic_sink, is_mic_driver_installed, install_mic_driver_silently
from server.camera_streamer import CameraStreamer, camera_streamer, is_webcam_driver_installed, install_webcam_driver_silently


def test_gamepad_manager():
    print("\n--- [1] Testing Gamepad Engine ---")
    gp = GamepadManager()
    mode = gp.mode
    print(f"OK: GamepadManager initialized successfully in mode: '{mode}'")
    assert mode in ("xinput", "sendinput", "linux_uinput")

    # Test Analog Sticks
    print("Testing stick deflections...")
    gp.set_stick("left", 0.75, -0.50)
    assert gp._axis_states["left"] == (0.75, -0.50)
    gp.set_stick("left", 1.5, -2.0) # Test clamping
    assert gp._axis_states["left"] == (1.0, -1.0)
    gp.set_stick("left", 0.0, 0.0)

    gp.set_stick("right", -0.35, 0.85)
    assert gp._axis_states["right"] == (-0.35, 0.85)
    gp.set_stick("right", 0.0, 0.0)
    print("OK: Analog sticks passed scaling and clamping tests.")

    # Test Triggers
    print("Testing analog triggers...")
    gp.set_trigger("LT", 0.95)
    assert abs(gp._trigger_states["left"] - 0.95) < 0.001
    gp.set_trigger("LT", 0.0)

    gp.set_trigger("RT", 1.5) # Clamping
    assert abs(gp._trigger_states["right"] - 1.0) < 0.001
    gp.set_trigger("RT", 0.0)
    print("OK: Triggers passed scaling and threshold tests.")

    # Test Digital Buttons
    print("Testing digital button presses...")
    for btn in ["A", "B", "X", "Y", "LB", "RB", "START", "BACK", "GUIDE", "DPAD_UP", "DPAD_DOWN"]:
        gp.set_button(btn, True)
        assert gp._button_states[btn] is True
        gp.set_button(btn, False)
        assert gp._button_states[btn] is False
    print("OK: Digital button events dispatched successfully.")

    # Test Gyro Super Steering & Aiming
    print("Testing Gyro Super Motion Engine...")
    gp.apply_gyro_steer(0.75)
    assert abs(gp._axis_states["left"][0] - 0.75) < 0.001
    gp.apply_gyro_steer(-0.6)
    assert abs(gp._axis_states["left"][0] - (-0.6)) < 0.001
    gp.apply_gyro_steer(0.0)
    assert abs(gp._axis_states["left"][0]) < 0.001

    gp.apply_gyro_aim(0.45, -0.35)
    assert abs(gp._axis_states["right"][0] - 0.45) < 0.001
    assert abs(gp._axis_states["right"][1] - (-0.35)) < 0.001
    gp.apply_gyro_aim(0.0, 0.0)
    assert abs(gp._axis_states["right"][0]) < 0.001
    assert abs(gp._axis_states["right"][1]) < 0.001
    print("OK: Gyro Super steer and aim successfully routed and scaled.")

    # Test Reset All
    gp.set_stick("left", 0.5, 0.5)
    gp.set_trigger("RT", 0.8)
    gp.set_button("A", True)
    gp.reset_all()
    assert gp._axis_states["left"] == (0.0, 0.0)
    assert gp._trigger_states["right"] == 0.0
    assert len(gp._button_states) == 0
    print("OK: reset_all() successfully returned controller to neutral.")


def test_microphone_sink():
    print("\n--- [2] Testing Microphone Sink ---")
    sink = MicrophoneSink(sample_rate=48000, channels=1)
    sink.start()
    assert sink.is_active is True
    print(f"OK: MicrophoneSink started (Active target device: '{sink.active_device_name}')")

    # Push sample 16-bit PCM buffer (480 samples = 960 bytes)
    dummy_pcm = b"\x00\x00" * 480
    sink.push_pcm_bytes(dummy_pcm)
    print("OK: Pushed 960-byte 16-bit 48kHz PCM buffer without errors.")

    sink.stop()
    assert sink.is_active is False
    print("OK: MicrophoneSink stopped cleanly.")


def test_camera_streamer():
    print("\n--- [3] Testing Camera Streamer ---")
    cam = CameraStreamer(width=1280, height=720, fps=30)
    cam.start_camera()
    assert cam.is_active is True
    print(f"OK: CameraStreamer started ({cam.target_width}x{cam.target_height} @ {cam.target_fps}fps)")

    # Push dummy JPEG bytes
    from PIL import Image
    import io
    img = Image.new("RGB", (640, 480), color=(0, 240, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    dummy_jpeg = buf.getvalue()

    cam.push_frame_bytes(dummy_jpeg)
    assert cam.frame_count >= 1
    print(f"OK: Ingested frame #{cam.frame_count} successfully.")

    cam.stop_camera()
    assert cam.is_streaming_live is False
    cam.close_device()
    assert cam.is_active is False
    print("OK: CameraStreamer stopped cleanly.")


def test_driver_helpers():
    print("\n--- [4] Testing Driver Diagnostic Helpers ---")
    vigem_ok = is_vigem_installed()
    print(f"OK: ViGEmBus status on host: {'INSTALLED' if vigem_ok else 'NOT INSTALLED (SendInput fallback active)'}")

    cam_ok = is_webcam_driver_installed()
    print(f"OK: Virtual Webcam Driver status: {'INSTALLED' if cam_ok else 'NOT INSTALLED (DirectShow/UnityCapture missing)'}")

    mic_ok = is_mic_driver_installed()
    print(f"OK: Virtual Audio Cable status: {'INSTALLED' if mic_ok else 'NOT INSTALLED (VB-Cable missing)'}")


if __name__ == "__main__":
    print("========================================")
    print("Running PCDeck Next-Gen Feature Test Suite")
    print("========================================")
    test_gamepad_manager()
    test_microphone_sink()
    test_camera_streamer()
    test_driver_helpers()
    print("\n========================================")
    print("ALL TESTS PASSED SUCCESSFULLY! (100% OK)")
    print("========================================")
