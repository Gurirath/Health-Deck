export interface BodyRegionDef {
  id: string;
  label: string;
  backendRegion: string;
  description: string;
  iconName: string;
  x: number; // percentage in diagram
  y: number;
}

export const BODY_REGIONS: BodyRegionDef[] = [
  {
    id: 'head',
    label: 'Head & Face',
    backendRegion: 'head',
    description: 'Headache, dizziness, eye, ear or sinus symptoms',
    iconName: 'Smile',
    x: 50,
    y: 12,
  },
  {
    id: 'throat',
    label: 'Throat & Neck',
    backendRegion: 'throat',
    description: 'Sore throat, difficulty swallowing, swollen glands',
    iconName: 'Activity',
    x: 50,
    y: 22,
  },
  {
    id: 'chest',
    label: 'Chest & Lungs',
    backendRegion: 'chest',
    description: 'Cough, chest tightness, palpitations, breathing',
    iconName: 'Heart',
    x: 50,
    y: 33,
  },
  {
    id: 'abdomen',
    label: 'Stomach & Abdomen',
    backendRegion: 'abdomen',
    description: 'Nausea, cramps, digestive issues, stomach pain',
    iconName: 'Shield',
    x: 50,
    y: 47,
  },
  {
    id: 'back',
    label: 'Back & Spine',
    backendRegion: 'other',
    description: 'Upper back tension, lower back stiffness, spinal aches',
    iconName: 'Layers',
    x: 50,
    y: 58,
  },
  {
    id: 'arm',
    label: 'Arms & Hands',
    backendRegion: 'limbs',
    description: 'Shoulder, elbow, wrist pain, numbness or joint ache',
    iconName: 'Hand',
    x: 23,
    y: 43,
  },
  {
    id: 'leg',
    label: 'Legs & Feet',
    backendRegion: 'limbs',
    description: 'Hip, knee, ankle, muscle soreness or walking strain',
    iconName: 'Footprints',
    x: 62,
    y: 77,
  },
  {
    id: 'skin',
    label: 'Skin & Rash',
    backendRegion: 'skin',
    description: 'Itching, redness, visible rash, bumps or irritation',
    iconName: 'Sparkles',
    x: 77,
    y: 43,
  },
  {
    id: 'other',
    label: 'Whole Body / General',
    backendRegion: 'other',
    description: 'Fever, fatigue, general malaise or unsure',
    iconName: 'HelpCircle',
    x: 38,
    y: 77,
  },
];
