import { Client, Functions } from 'appwrite';

const Appwrite_Function = process.env.Appwrite_Function;
const Appwrite_Endpoint = process.env.Appwrite_Endpoint;
const Appwrite_Project = process.env.Appwrite_Project;

const client = new Client()
      .setEndpoint(Appwrite_Endpoint)
      .setProject(Appwrite_Project);
const functions = new Functions(client);

const t_feed_url = document.querySelector('#t_feed_url');

async function create(event) {
  event.preventDefault();

  const url = document.querySelector('#rssUrl');
  const lang = document.querySelector('#language');
  const result = document.querySelector('#result');
  const error_msg = document.querySelector('#error_msg');
  const loading = document.querySelector('#loading');
  
  try {
    const urlObject = new URL(url.value);
    const translation_update = document.querySelector('#translation_update');
    const translation_process = document.querySelector('#translation_process');

    if (lang.value === "") {
      throw new Error("Invalid Language!");
    }
    
    // Initialize
    error_msg.textContent = "";
    result.style.display = 'none';
    translation_process.style.display = 'unset';
    translation_update.innerHTML = "Translation in progress. Updates shortly";

    let payload = {
      feed_url: url.value,
      to_lang: lang.value
    };
    console.log(payload);
    loading.style.display = 'block';

    const promise = await functions.createExecution(Appwrite_Function, JSON.stringify(payload));
    let translated_feed_url = promise.response
    if (translated_feed_url!='error') {
      result.style.display = 'block';
      t_feed_url.value = translated_feed_url;
      payload = {
        feed_url: url.value,
        to_lang: lang.value,
        update: true
      };

      functions.createExecution(Appwrite_Function, JSON.stringify(payload))
        .then(res => {
          console.log(res);
          if (res.response != 'error') {       
            translation_update.innerHTML += ' ✔';
          }else{
            //translation_update.innerHTML += ' ✘';
            console.error(res);
          }
          translation_process.style.display = 'none';
        })
        .catch(error => {
          console.error(error);
          translation_process.style.display = 'none';
          //translation_update.innerHTML += ' ✘';
        });

      url.value = null;
    } else {
      result.style.display = 'none';
      //throw new Error(JSON.stringify(res));
      throw new Error('Please check the URL and try again')
    }

  } catch (error) {
    error_msg.textContent = error.message;
    console.error(error);
  } finally {
    loading.style.display = 'none';
  }
}

function copy(event){
  event.preventDefault();
  const button = document.querySelector('#copy');
  const text = t_feed_url.value;
  
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

//add event listener to button
document.querySelector('#create').addEventListener('click', create);
//<button id="copy" class="success stack">Copy</button>
document.querySelector('#copy').addEventListener("click", copy);

