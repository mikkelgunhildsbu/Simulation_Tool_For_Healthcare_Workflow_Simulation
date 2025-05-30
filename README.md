# Simulation tool for healthcare workflow simulation
###_A case study in the histology laboratory at Haukeland university hospital_

This repository is part of a master’s thesis focused on developing a discrete event simulation tool for the histology laboratory at Haukeland University Hospital.

⚠️ Due to privacy and data protection constraints, the full implementation and dataset are not publicly available. As a result, not all intended features are functional in this public version. However, the repository demonstrates core simulation functionality.

###How to Run the Simulation

1. Clone or fork the repository:

`git clone https 
`

`
cd reponame
`

2. Install the required dependencies:

`
pip install -r requirments.txt
`

3. Run the simulation:

`python main.py`

### Thesis Components

This repository includes the implementation of **all components referenced throughout the thesis**, structured as follows:

- **`stages/`** – Contains the implementation of all histology workflow stages (e.g., accessioning, grossing, embedding, staining, etc).
- **`simSetup/`** – Handles the simulation setup, including queue creation, resource allocation, and initializing queue state.
- **`components/`** – Includes case arrival, case attributes, case splitting, rework handling, and service time distributions.
- **`FrontEnd/`** – Contains the web application interface for interacting with or visualizing the simulation.
- **`tests/`** – Provides validation scripts for comparing simulation output against historical data.

> **Note:** Some paths and data sources are removed due to privacy constraints, but the full simulation logic and structure are intact.
