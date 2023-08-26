import { Client, Functions } from 'appwrite';

const client = new Client()
      .setEndpoint('https://appwrite.rsstranslator.com/v1')
      .setProject('RSS_Translator');
const functions = new Functions(client);
const langMap = {
      EN: "English",
      ES: "español",
      ZH: "中文",
      AR: "العربية",
      PT: "português",
      RU: "русский",
      JA: "日本語",
      FR: "français",
      DE: "Deutsch",
      IT: "italiano",
      KO: "한국어",
      TR: "Türkçe",
      VI: "Tiếng Việt",
      PL: "polski",
      ID: "Bahasa Indonesia",
      NL: "Nederlands",
      BN: "বাংলা",
      TA: "தமிழ்",
      FA: "فارسی",
      TH: "ไทย",
      UK: "українська",
      RO: "română",
      SV: "svenska",
      HU: "magyar",
      EL: "Ελληνικά",
      CS: "čeština",
      DA: "dansk",
      FI: "suomi",
      BG: "български",
      HR: "hrvatski",
      LT: "lietuvių",
      SK: "slovenčina",
      SL: "slovenščina",
      ET: "eesti",
      LV: "latviešu",
      NB: "norsk bokmål",
    };
const t_feed_url = document.querySelector('#t_feed_url');
//add options to language dropdown
const langDropdown = document.querySelector('#language');
for (const [key, value] of Object.entries(langMap)) {
  const option = document.createElement('option');
  option.value = key;
  option.text = value;
  langDropdown.appendChild(option);
};

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
  
    const payload = {
      feed_url: url.value,
      to_lang: lang.value
    };
    console.log(payload);
    loading.style.display = 'block';
    const promise = await functions.createExecution('rss_action', JSON.stringify(payload));
    let res = promise.response.replace(/\\\\/g, "\\");
    res = JSON.parse(res);
    let translated_feed_url = res.t_feed_url || null;

    if (translated_feed_url) {
      result.style.display = 'block';
      t_feed_url.value = translated_feed_url;
      url.value = null;
    } else {
      result.style.display = 'none';
      throw new Error("Please check the URL and try again!");
    }

  } catch (error) {
    error_msg.textContent = error.message;
    console.error(error);
  } finally {
    loading.style.display = 'none';
  }
}

function copy(){
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

