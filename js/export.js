import { Client, Functions } from 'appwrite';

const Appwrite_Endpoint = process.env.Appwrite_Endpoint;
const Appwrite_Project = process.env.Appwrite_Project;

const client = new Client()
  .setEndpoint(Appwrite_Endpoint)
  .setProject(Appwrite_Project);
const functions = new Functions(client);

function copy(event) {
  event.preventDefault();
  const button = document.querySelector('#copy');
  const text = result_text.value;

  navigator.clipboard.writeText(text)
    .then(() => {
      console.log("Text copied to clipboard");
      button.innerHTML += ' &#10004;';

      setTimeout(() => {
        button.innerHTML = "Copy";
      }, 3000);
    })
    .catch((error) => console.error("Could not copy text: ", error));
}

function o_url_check(event) {
  event.preventDefault();
  const textarea = document.querySelector('#t_feed_url');
  const result = document.querySelector('#result');
  const result_text = document.querySelector('#result_text');
  const error_msg = document.querySelector('#error_msg');
  const loading = document.querySelector('#loading');
  let responseBody;
  let urls = textarea.value.split('\n')
    .map(url => url.trim())
    .filter(url => url.length);

  try {
    if (!urls.length) return;

    error_msg.textContent = "";
    result.style.display = 'none';
    loading.style.display = 'block';

    let payload = {
      urls: urls
    };
    console.log(payload);

    functions.createExecution('export', JSON.stringify(payload))
      .then(response => {
        console.log("Response:", response);
        responseBody = JSON.parse(JSON.parse(response.responseBody));
        console.log(responseBody);

        result.style.display = 'block';
        result_text.value = responseBody.join('\n') || 'Nothing to export. Please verify the URL or try again';
      })
      .catch(e => {
        throw e;
      })
      .finally(() => {
        loading.style.display = 'none';
      });

  } catch (error) {
    error_msg.innerHTML = error.message.replace(/\n/g, '<br>');
    console.error(error);
  }
}

//<button id="copy" class="success stack">Copy</button>
document.querySelector('#copy').addEventListener("click", copy);

document.querySelector('#export').addEventListener("click", o_url_check);

