function copyToClipboard(element) {
    var url = element.getAttribute('data-url');
    var tempInput = document.createElement("input");
    tempInput.value = url;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand("copy");
    document.body.removeChild(tempInput);
    
    // 保存原始的按钮文本
    var originalText = element.innerText || element.textContent;
 
    // 将按钮文本更改为✔
    element.innerText = '✔';
 
    // 在3秒后恢复原始的按钮文本
    setTimeout(function() {
        element.innerText = originalText;
    }, 3000);
 }
 