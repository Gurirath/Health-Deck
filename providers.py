"""Kiosk input providers, abstracted so the agent and UI never touch a
source directly.

Vitals providers return a dict with these five keys:

    spo2          blood oxygen saturation, percent
    temp_c        body temperature, degrees Celsius
    hr            heart rate, beats per minute
    systolic_bp   systolic blood pressure, mmHg
    diastolic_bp  diastolic blood pressure, mmHg

Symptom-location providers return one of BODY_REGIONS (or a finer string a
future 3D body map produces). Swapping in a real sensor module or a tappable
body map means adding a new class here; nothing else in the app changes.
"""

import streamlit as st

VITALS_KEYS = ("spo2", "temp_c", "hr", "systolic_bp", "diastolic_bp")

BODY_REGIONS = ["head", "chest", "abdomen", "limbs", "throat", "skin", "other"]


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


class SymptomLocationProvider:
    """Interface for capturing the body location of the chief complaint."""

    def get_location(self):
        raise NotImplementedError


class SelectboxLocationProvider(SymptomLocationProvider):
    """The current input: a single selectbox of coarse body regions."""

    def get_location(self):
        return st.selectbox("Where is the problem?", BODY_REGIONS)


class BodyMapLocationProvider(SymptomLocationProvider):
    """Reserved for the Three.js tappable body map. Not built yet."""

    def get_location(self):
        raise NotImplementedError(
            "BodyMapLocationProvider is a placeholder for the glTF body map. "
            "Implement get_location() to return the tapped region as a string."
        )
