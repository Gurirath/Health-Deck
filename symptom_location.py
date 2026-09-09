"""Where on the body the complaint is, abstracted behind a small interface.

Today this is a selectbox of coarse body regions. A teammate is building a
tappable 3D body map (Blender model exported to glTF, rendered with
Three.js). That becomes a new provider implementing the same get_location()
method and returning one of BODY_REGIONS (or a finer string the dashboard
can still display); the agent state, persistence, and dashboard need no
changes when it lands.
"""

import streamlit as st

BODY_REGIONS = ["head", "chest", "abdomen", "limbs", "throat", "skin", "other"]


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
