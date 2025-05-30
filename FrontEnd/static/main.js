function renderActorSettingsSections() {
  const container = document.getElementById("actor-machine-settings-container");
  const templateHtml = document.getElementById("actor-settings-template").innerHTML;
  const numDays = parseInt(document.getElementById("sim_days").value) || 1;

  container.innerHTML = "";

  for (let day = 1; day <= numDays; day++) {
    container.innerHTML += templateHtml.replace(/DAY/g, day);
  }

  attachAllActorListeners(numDays);
}

document.addEventListener("DOMContentLoaded", function () {
  renderActorSettingsSections();

  document.getElementById("sim_days").addEventListener("change", function () {
    renderActorSettingsSections();
  });
});

function updateHiddenInputWithShift(activity, day) {
  const listElem = document.getElementById(`selected-${activity}-${day}`);
  const hiddenInput = document.getElementById(`input-${activity}-${day}`);
  const items = listElem.querySelectorAll('li');

  const actors = Array.from(items).map(li => {
    const parts = li.textContent.split(" - ");
    return {
      name: parts[0].trim(),
      half_day: parts[1].trim() === "Half Day"
    };
  });

  hiddenInput.value = JSON.stringify(actors);
}

function addActorWithShift(activity, day) {
  const selectElem = document.getElementById(`select-${activity}-${day}`);
  const actorName = selectElem.value;
  const shiftRadio = document.querySelector(`input[name="shift-${activity}-${day}"]:checked`);
  const shift = shiftRadio ? shiftRadio.value : "full";
  const listElem = document.getElementById(`selected-${activity}-${day}`);

  if (listElem.querySelector(`[data-actor="${actorName}"]`)) {
    alert("This actor is already selected.");
    return;
  }

  const li = document.createElement("li");
  li.setAttribute("data-actor", actorName);
  li.textContent = actorName + " - " + (shift === "half" ? "Half Day" : "Full Day");

  li.addEventListener("click", function () {
    li.remove();
    updateHiddenInputWithShift(activity, day);
  });

  listElem.appendChild(li);
  updateHiddenInputWithShift(activity, day);
}

function attachAllActorListeners(numDays) {
  const activities = [
    "accessioning",
    "grossing",
    "manualEmbedding",
    "manualSectioning",
    "decalcination",
    "manualStaining",
    "finalReportFinished"
  ];

  activities.forEach(activity => {
    for (let day = 1; day <= numDays; day++) {
      const listElem = document.getElementById(`selected-${activity}-${day}`);
      if (listElem) {
        listElem.querySelectorAll("li").forEach(li => {
          li.addEventListener("click", function () {
            li.remove();
            updateHiddenInputWithShift(activity, day);
          });
        });
      }
    }
  });
}

// ------------------------------
// D3 Visualization & State Initialization
// ------------------------------
async function initializeState() {
  try {
    const response = await fetch("http://127.0.0.1:5000/initialize_state");
    const data = await response.json();
    if (data.error) {
      console.error("Error loading state:", data.error);
      return;
    }

    d3.select("#queue-state").html("");
    const width = 1200, height = 200, margin = 50;
    const svg = d3.select("#queue-state").append("svg").attr("width", width).attr("height", height);

    const nodes = [
      { id: "accessioning", label: "Accessioning" },
      { id: "grossing", label: "Grossing" },
      { id: "decalcination", label: "Decalcination" },
      { id: "processing", label: "Processing" },
      { id: "embedding", label: "Embedding" },
      { id: "manual_sectioning", label: "Manual Sectioning" },
      { id: "automatic_staining", label: "Automatic Staining" },
      { id: "stainingIHC", label: "Staining IHC" },
      { id: "manual_staining", label: "Manual Staining" },
      { id: "scanning", label: "Scanning" },
      { id: "final_report", label: "Final Report Finished" }
    ];

    nodes.forEach((node, i) => {
      node.x = margin + i * ((width - 2 * margin) / (nodes.length - 1));
      node.y = height / 2;
    });

    const maxQueue = d3.max(Object.values(data.queue_state));
    const colorScale = d3.scaleLinear().domain([0, maxQueue]).range(["green", "red"]);

    svg.selectAll("circle")
      .data(nodes)
      .enter()
      .append("circle")
      .attr("cx", d => d.x)
      .attr("cy", d => d.y)
      .attr("r", 30)
      .attr("fill", d => colorScale(data.queue_state[d.id + "_queue"] || 0))
      .attr("stroke", "#000")
      .attr("stroke-width", 2);

    svg.selectAll(".queue-text")
      .data(nodes)
      .enter()
      .append("text")
      .attr("class", "queue-text")
      .attr("x", d => d.x)
      .attr("y", d => d.y + 5)
      .attr("text-anchor", "middle")
      .attr("fill", "white")
      .attr("font-size", "14px")
      .attr("font-weight", "bold")
      .text(d => data.queue_state[d.id + "_queue"] || 0);

    svg.selectAll(".node-label")
      .data(nodes)
      .enter()
      .append("text")
      .attr("class", "node-label")
      .attr("x", d => d.x)
      .attr("y", d => d.y + 50)
      .attr("text-anchor", "middle")
      .attr("fill", "#333")
      .attr("font-size", "12px")
      .text(d => d.label);

  } catch (error) {
    console.error("Error fetching queue state:", error);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await initializeState();

  const updateActorDiv = document.getElementById("update_actor");
  if (updateActorDiv) {
    updateActorDiv.innerHTML = `
      <button id="updateActorsBtn" type="button" class="btn btn-primary me-2">Update Actors from Yesterday</button>
      <button id="resetActorsBtn" type="button" class="btn btn-warning">Reset Actors</button>
    `;

    document.getElementById("updateActorsBtn").addEventListener("click", () => {
      fetch("http://127.0.0.1:5000/update_based", { method: "POST" })
        .then(response => response.ok ? response.text() : Promise.reject(response))
        .then(() => {
          alert("Actors updated successfully!");
          window.location.reload();
        })
        .catch(error => {
          console.error("Error updating actors:", error);
          alert("Error updating actors.");
        });
    });

    document.getElementById("resetActorsBtn").addEventListener("click", () => {
      fetch("http://127.0.0.1:5000/reset_actors", { method: "POST" })
        .then(response => response.ok ? response.text() : Promise.reject(response))
        .then(() => {
          alert("Actors reset successfully!");
          window.location.reload();
        })
        .catch(error => {
          console.error("Error resetting actors:", error);
          alert("Error resetting actors.");
        });
    });
  }
});
