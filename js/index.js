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

    if (lang.value === "") {
      throw new Error("Invalid Language!");
    }
    
    // Initialize
    error_msg.textContent = "";
    result.style.display = 'none';

    let payload = {
      feed_url: url.value,
      to_lang: lang.value
    };
    console.log(payload);
    loading.style.display = 'block';

    const promise = await functions.createExecution(Appwrite_Function, JSON.stringify(payload));
    let translated_feed_url = promise.responseBody
    console.log("Response:",translated_feed_url);

    if (translated_feed_url==''){
      result.style.display = 'none';
      throw new Error('Ops! Please try again!');
    }else if (translated_feed_url=='null') {
      result.style.display = 'none';
      throw new Error('Sorry, Not in database yet.');
    }else if (translated_feed_url=='error') {
      result.style.display = 'none';
      throw new Error('Invalid RSS feed URL.\nPlease verify the URL and try again');
    }else {
      result.style.display = 'block';
      t_feed_url.value = translated_feed_url;
    }
 
  } catch (error) {
    error_msg.innerHTML = error.message.replace(/\n/g, '<br>');
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

