var el = x => document.getElementById(x);

function showPicker() {
  el("file-input").click();
}

function showPicked(input) {
  if (!input.files.length) return;
  el("upload-label").textContent = input.files[0].name;
  var reader = new FileReader();
  reader.onload = function(e) {
    el("image-picked").src = e.target.result;
    el("image-picked").className = "";
  };
  reader.readAsDataURL(input.files[0]);
}

function analyze() {
  var uploadFiles = el("file-input").files;
  if (uploadFiles.length !== 1) {
    alert("Please select a file to analyze!");
    return;
  }

  el("analyze-button").innerHTML = "Analyzing...";
  var xhr = new XMLHttpRequest();
  xhr.open("POST", "/analyze", true);
  xhr.onerror = function() {
    el("result-label").textContent = "Unable to reach the classifier.";
    el("analyze-button").textContent = "Analyze";
  };
  xhr.onload = function(e) {
    if (this.readyState === 4) {
      try {
        var response = JSON.parse(e.target.responseText);
        el("result-label").textContent = this.status === 200
          ? `Result = ${response["result"]}`
          : (response.error || "Unable to analyze this image.");
      } catch (error) {
        el("result-label").textContent = "Unable to analyze this image.";
      }
    }
    el("analyze-button").innerHTML = "Analyze";
  };

  var fileData = new FormData();
  fileData.append("file", uploadFiles[0]);
  xhr.send(fileData);
}

