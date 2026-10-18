const form=document.getElementById("form");
const status=document.getElementById("status");

form.addEventListener("submit",async(e)=>{
    e.preventDefault();
    const res=await fetch("/api/messages",{
        method: "POST",
        headers: {"Content-Type": "application/json", "X-CSRF": form.dataset.csrf},
        body: JSON.stringify({text: form.text.value}),
    });
    if (res.redirected){window.location =res.url; return;}//session ended to the loginnn hyah
    const data=await res.json();
    status.textContent=res.ok? "Sent. your name was not attached.":data.error;
    if (res.ok) form.reset();
});