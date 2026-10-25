(() => {
  const content = document.getElementById('sharedConversation');
  const pathParts = window.location.pathname.split('/').filter(Boolean);
  const shareId = pathParts[pathParts.length - 1] || '';

  function showError(message) {
    content.replaceChildren();
    const error = document.createElement('p');
    error.className = 'shared-status shared-error';
    error.textContent = message;
    content.appendChild(error);
    content.setAttribute('aria-busy', 'false');
  }

  async function loadSharedConversation() {
    try {
      const response = await fetch(`/shared/${encodeURIComponent(shareId)}`, {
        headers: { Accept: 'application/json' },
        credentials: 'omit',
        cache: 'no-store'
      });
      if (!response.ok) throw new Error('This shared conversation is unavailable.');
      const snapshot = await response.json();
      if (!snapshot || typeof snapshot.title !== 'string' || !Array.isArray(snapshot.messages)) {
        throw new Error('This shared conversation is unavailable.');
      }

      const title = document.createElement('h1');
      title.textContent = snapshot.title;
      content.replaceChildren(title);
      snapshot.messages.forEach((message) => {
        if (!message || !['user', 'assistant'].includes(message.sender) || typeof message.text !== 'string') return;
        const article = document.createElement('article');
        article.className = 'shared-message';
        const role = document.createElement('h2');
        role.textContent = message.sender === 'user' ? 'You' : 'Assistant';
        const text = document.createElement('p');
        text.textContent = message.text;
        article.append(role, text);
        content.appendChild(article);
      });
      if (snapshot.messages.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'shared-status';
        empty.textContent = 'No messages in this conversation.';
        content.appendChild(empty);
      }
      content.setAttribute('aria-busy', 'false');
      document.title = `${snapshot.title} · Shared CWP conversation`;
    } catch (error) {
      showError(error.message || 'This shared conversation is unavailable.');
    }
  }

  loadSharedConversation();
})();
