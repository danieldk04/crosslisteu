chrome.storage.sync.get({ serverUrl: "http://localhost:8001" }, (s) => {
  document.getElementById("serverUrl").value = s.serverUrl;
});

document.getElementById("save").addEventListener("click", () => {
  const url = document.getElementById("serverUrl").value.trim();
  chrome.storage.sync.set({ serverUrl: url }, () => {
    document.getElementById("status").textContent = "Opgeslagen ✓";
    setTimeout(() => (document.getElementById("status").textContent = ""), 2000);
  });
});
