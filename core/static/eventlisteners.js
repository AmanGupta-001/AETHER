window.addEventListener('keydown', (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault(); // Prevent adding newline to textarea
        sendMessage();
    }
});