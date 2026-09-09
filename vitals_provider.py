"""Vitals capture, abstracted so the agent and UI never touch the source directly.

A provider returns a dict with these five keys:

    spo2          blood oxygen saturation, percent
    temp_c        body temperature, degrees Celsius
    hr            heart rate, beats per minute
    systolic_bp   systolic blood pressure, mmHg
    diastolic_bp  diastolic blood pressure, mmHg

Swap ManualVitalsProvider for SensorVitalsProvider once the hardware module
is ready; nothing else in the app changes.
"""

import streamlit as st

VITALS_KEYS = ("spo2", "temp_c", "hr", "systolic_bp", "diastolic_bp")


class VitalsProvider:
    """Interface for anything that can hand the kiosk a set of vitals."""

    def get_vitals(self):
        raise NotImplementedError


class ManualVitalsProvider(VitalsProvider):
    """The manual-entry stand-in: sidebar sliders a staff member sets by hand."""

    def get_vitals(self):
        st.header("Vitals")
        spo2 = st.slider("SpO2 (%)", 80, 100, 98)
        temp_c = st.slider("Temperature (C)", 35.0, 41.0, 37.0, 0.1)
        hr = st.slider("Heart rate (bpm)", 40, 160, 75)
        systolic = st.slider("Systolic BP", 70, 200, 120)
        diastolic = st.slider("Diastolic BP", 40, 130, 80)
        return {
            "spo2": spo2,
            "temp_c": temp_c,
            "hr": hr,
            "systolic_bp": systolic,
            "diastolic_bp": diastolic,
        }


class SensorVitalsProvider(VitalsProvider):
    """Stub for the real sensor module.

    The hardware team implements get_vitals() to read the sensor board and
    return a dict with exactly the keys in VITALS_KEYS:
    spo2, temp_c, hr, systolic_bp, diastolic_bp. Numeric values only, using
    the units documented at the top of this module. It must not import
    Streamlit or otherwise depend on the UI.
    """

    def get_vitals(self):
        raise NotImplementedError(
            "SensorVitalsProvider is a stub. Implement get_vitals() to read the "
            "sensor module and return a dict with keys spo2, temp_c, hr, "
            "systolic_bp, diastolic_bp."
        )
