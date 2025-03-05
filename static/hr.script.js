// Sample candidate data (replace with API fetch in production)
const candidates = [
    { id: 1, name: "John Doe", score: 85, status: "Shortlisted" },
    { id: 2, name: "Jane Smith", score: 78, status: "Reviewed" },
    { id: 3, name: "Bob Johnson", score: 92, status: "Submitted" },
];

// Render candidate cards
function renderCandidates(filteredCandidates) {
    const grid = document.getElementById("candidate-grid");
    grid.innerHTML = "";
    filteredCandidates.forEach(candidate => {
        const card = document.createElement("div");
        card.className = "candidate-card";
        card.innerHTML = `
            <input type="checkbox" name="candidate" value="${candidate.id}">
            <h3>${candidate.name}</h3>
            <p>Score: ${candidate.score}/100</p>
            <p>Status: ${candidate.status}</p>
        `;
        grid.appendChild(card);
    });
}

// Initial render
renderCandidates(candidates);

// Search functionality
document.getElementById("search-input").addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase();
    const filtered = candidates.filter(c => c.name.toLowerCase().includes(query));
    renderCandidates(filtered);
});

// Filter by status
document.getElementById("filter-status").addEventListener("change", (e) => {
    const status = e.target.value;
    const filtered = status === "all" ? candidates : candidates.filter(c => c.status.toLowerCase() === status);
    renderCandidates(filtered);
});

// Logout (placeholder)
document.getElementById("logout-btn").addEventListener("click", () => {
    alert("Logging out...");
    // Add logout logic here
});

// Batch actions (placeholder)
document.getElementById("select-all").addEventListener("click", () => {
    document.querySelectorAll('input[name="candidate"]').forEach(checkbox => checkbox.checked = true);
});

document.getElementById("schedule-interviews").addEventListener("click", () => {
    const selected = Array.from(document.querySelectorAll('input[name="candidate"]:checked'))
        .map(cb => cb.value);
    if (selected.length > 0) {
        alert(`Scheduling interviews for candidates: ${selected.join(", ")}`);
        // Add scheduling logic here
    } else {
        alert("Please select at least one candidate.");
    }
});

document.getElementById("export-btn").addEventListener("click", () => {
    alert("Exporting candidate data as CSV...");
    // Add export logic here
});