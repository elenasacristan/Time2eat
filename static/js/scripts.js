// https://developer.mozilla.org/en-US/docs/Web/API/FileReader/readAsDataURL

function previewFile() {
  var preview = document.querySelector(".img-details img");
  var file = document.querySelector("input[type=file]").files[0];
  var reader = new FileReader();

  reader.addEventListener(
    "load",
    function() {
      preview.src = reader.result;
    },
    false
  );

  if (file) {
    reader.readAsDataURL(file);
  }
}
