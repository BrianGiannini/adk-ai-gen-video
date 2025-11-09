// --- State ---
let currentGoogleToken = null;

// --- 1. Google Sign-In Initialization ---
window.onload = function() {
    
    const GOOGLE_CLIENT_ID = "362118722455-e2qv32anp5nhg0kt99ckmtg1ltd7p2a2.apps.googleusercontent.com";

    google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleSignIn,
        auto_select: true  // Attempt to sign in silently on page load
    });
    
    google.accounts.id.renderButton(
        document.getElementById("g_id_signin"),
        { theme: "outline", size: "large", width: "300" } 
    );
    
    // Try to auto-sign-in. 
    // If it works, handleSignIn() is called.
    // If it fails, we show the anonymous state.
    google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            // Auto-sign-in failed. Show both request and sign-in.
            updateUI('anon');
        }
    });
};

// --- 2. Handle User Sign-In ---
async function handleSignIn(googleUser) {
    currentGoogleToken = googleUser.credential; // This is the ID Token
    
    // Now that they're signed in, check their status
    try {
        const res = await fetch("/check-status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ idToken: currentGoogleToken })
        });

        const data = await res.json();
        
        if (data.status === "approved") {
            updateUI('approved');
        } else if (data.status === "pending") {
            updateUI('pending');
        } else {
            // User signed in, but is not in our DB
            updateUI('not_found');
        }
    } catch (e) {
        showMessage("error", "Could not check status: " + e.message);
    }
}

// --- 3. Handle Requesting Access ---
async function requestAccess() {
    const email = document.getElementById("email-input").value;
    if (!email) {
        showMessage("error", "Please enter an email address.");
        return;
    }

    try {
        const res = await fetch("/request-access", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email })
        });
        const data = await res.json();
        
        if (data.status === "success") {
            let successMessage = `Access requested for ${email}! To get approved, please send an email or message to brian.giannini.1@gmail.com.`;
            showMessage("success", successMessage);
            
            // Show the "pending" message
            updateUI('pending');
        } else {
            showMessage("error", data.message);
        }
    } catch (e) {
        showMessage("error", "An error occurred: " + e.message);
    }
}

// --- 4. Handle Submitting a Prompt ---
async function submitPrompt() {
    if (!currentGoogleToken) {
        showMessage("error", "You must be signed in.");
        return;
    }

    const prompt = document.getElementById("prompt-input").value;
    const btn = document.getElementById("generate-btn");

    if (!prompt) {
        showMessage("error", "Please enter a prompt.");
        return;
    }

    btn.disabled = true;
    btn.innerText = "Generating... (this can take a minute)";
    showMessage("info", "Request sent. Waiting for video generation...");
    
    // Hide the download link, but keep the video player visible
    document.getElementById("download-link").style.display = "none";
    
    try {
        const res = await fetch("/submit-prompt", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + currentGoogleToken
            },
            body: JSON.stringify({ prompt: prompt })
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.error || "An unknown error occurred.");
        }
        
        const videoPlayer = document.getElementById("video-player");
        const downloadLink = document.getElementById("download-link");

        videoPlayer.src = data.video_url;
        downloadLink.href = data.video_url;

        sessionStorage.setItem("lastVideoUrl", data.video_url);

        // Show the download link
        downloadLink.style.display = "block";

        videoPlayer.load();

        showMessage("success", "Video generated successfully! Press play to watch.");

    } catch (e) {
        showMessage("error", e.message);
    } finally {
        btn.disabled = false;
        btn.innerText = "Generate";
    }
}

// --- UI Helper Functions ---
function showMessage(type, text) {
    const msg = document.getElementById("message");
    msg.className = type;
    msg.innerText = text;
    msg.style.display = "block";
}

// This function controls which sections are visible
function updateUI(state) {
    // Hide all main sections
    document.getElementById("request-access-form").style.display = "none";
    document.getElementById("google-signin-btn").style.display = "none";
    document.getElementById("pending-message").style.display = "none";
    document.getElementById("not-found-message").style.display = "none";
    document.getElementById("app-content").style.display = "none";
    document.getElementById("video-result").style.display = "none";

    // Show sections based on the state
    if (state === 'anon') {
        // Not logged in (auto-sign-in failed)
        document.getElementById("request-access-form").style.display = "block";
        document.getElementById("google-signin-btn").style.display = "block";
    } else if (state === 'pending') {
        // Logged in, but pending approval
        document.getElementById("pending-message").style.display = "block";
    } else if (state === 'approved') {
        // Logged in and approved
        document.getElementById("app-content").style.display = "block";
        document.getElementById("video-result").style.display = "block";
        
        const lastUrl = sessionStorage.getItem("lastVideoUrl");
        if (lastUrl) {
            const videoPlayer = document.getElementById("video-player");
            const downloadLink = document.getElementById("download-link");
            
            videoPlayer.src = lastUrl;
            downloadLink.href = lastUrl;
            
            videoPlayer.load();
            downloadLink.style.display = "block";
        }
        
    } else if (state === 'not_found') {
        // Logged in, but not in our database
        document.getElementById("request-access-form").style.display = "block";
        document.getElementById("not-found-message").style.display = "block";
    }
}