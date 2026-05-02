import { useEffect, useMemo, useRef, useState } from "react";
import api from "../services/api";

const QUICK_PROMPTS = [
  {
    label: "Today Focus",
    prompt: "What should I focus on today based on CRM risks, opportunities, signals, and pending actions?",
    description: "Daily operating priorities",
  },
  {
    label: "Executive Brief",
    prompt: "Give me an executive brief for the CRM business.",
    description: "Management-ready summary",
  },
  {
    label: "Risk Accounts",
    prompt: "Which customers are at risk and why?",
    description: "Retention and complaints",
  },
  {
    label: "Growth Opportunities",
    prompt: "Which customers are the best growth or upsell opportunities?",
    description: "Revenue opportunities",
  },
  {
    label: "Pending Actions",
    prompt: "Summarize the most important pending actions and what I should do next.",
    description: "Execution queue review",
  },
  {
    label: "Import Health",
    prompt: "Show me recent import history and any data quality warnings.",
    description: "Data pipeline status",
  },
];

const EXAMPLE_QUESTIONS = [
  "Summarize the business in 5 bullet points.",
  "Which customers need attention?",
  "What are the biggest risks in the CRM?",
  "Which leads or signals are unmatched?",
  "What should the sales team do next?",
  "Give me a weekly CRM action plan.",
];

function AIChat() {
  const [messages, setMessages] = useState([
    {
      role: "ai",
      content:
        "Welcome to your AI CRM Copilot. I can analyze customers, orders, signals, actions, imports, risks, opportunities, and executive priorities.",
      meta: "System ready",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copilotMode, setCopilotMode] = useState("operator");

  const [isListening, setIsListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [voiceError, setVoiceError] = useState("");

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setVoiceSupported(false);
      return;
    }

    setVoiceSupported(true);

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onstart = () => {
      setIsListening(true);
      setVoiceError("");
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.onerror = (event) => {
  setIsListening(false);

  console.error("Speech recognition error:", event.error, event);

  if (event.error === "not-allowed") {
    setVoiceError(
      "Microphone permission was denied. Please allow microphone access from browser site settings."
    );
  } else if (event.error === "no-speech") {
    setVoiceError("No speech detected. Please speak clearly and try again.");
  } else if (event.error === "audio-capture") {
    setVoiceError(
      "No microphone was found or the browser cannot access it. Check your microphone device."
    );
  } else if (event.error === "network") {
    setVoiceError(
      "Speech recognition network error. Chrome speech recognition may require internet access."
    );
  } else if (event.error === "aborted") {
    setVoiceError("Voice recognition was stopped before completing.");
  } else if (event.error === "service-not-allowed") {
    setVoiceError(
      "Speech recognition service is not allowed in this browser or environment. Try Chrome."
    );
  } else {
    setVoiceError(`Voice recognition failed: ${event.error}`);
  }
};

    recognition.onresult = (event) => {
      let finalTranscript = "";
      let interimTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const transcript = event.results[i][0].transcript;

        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      setInput((prev) => {
        const baseText = prev.trim();
        const spokenText = (finalTranscript || interimTranscript).trim();

        if (!spokenText) return prev;
        if (!baseText) return spokenText;

        return `${baseText} ${spokenText}`.trim();
      });
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const modePromptPrefix = useMemo(() => {
    if (copilotMode === "executive") {
      return "Answer like an executive CRM advisor. Be concise, strategic, and management-ready. Question: ";
    }

    if (copilotMode === "sales") {
      return "Answer like a sales operations CRM copilot. Focus on customers, opportunities, follow-ups, and revenue. Question: ";
    }

    if (copilotMode === "risk") {
      return "Answer like a customer success risk analyst. Focus on complaints, high-risk signals, retention, and urgent actions. Question: ";
    }

    return "Answer like a CRM operations copilot. Focus on practical next actions. Question: ";
  }, [copilotMode]);

  const sendQuestion = async (questionText) => {
    const question = questionText.trim();
    if (!question) return;

    const userMessage = {
      role: "user",
      content: question,
      meta: getModeLabel(copilotMode),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const finalQuestion = `${modePromptPrefix}${question}`;

      const response = await api.post("/ai/chat", null, {
        params: { question: finalQuestion },
      });

      const aiMessage = {
        role: "ai",
        content:
          response.data?.answer ||
          "I could not find a useful answer from the CRM data.",
        meta: getModeLabel(copilotMode),
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error("AI chat error:", error);

      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          content:
            "I could not process that request. Make sure the backend is running and the Groq API key is configured.",
          meta: "Error",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    await sendQuestion(input);
  };

  const handleQuickPrompt = async (prompt) => {
    await sendQuestion(prompt);
  };

  const handleExampleClick = (question) => {
    setInput(question);
  };

  const handleKeyDown = async (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      await handleSend();
    }
  };

  const startVoiceInput = () => {
    if (!voiceSupported || !recognitionRef.current) {
      setVoiceError("Voice input is not supported in this browser.");
      return;
    }

    setVoiceError("");

    if (isListening) {
      recognitionRef.current.stop();
      return;
    }

    try {
      recognitionRef.current.start();
    } catch (error) {
      console.error("Voice start error:", error);
      setVoiceError("Could not start voice input. Please try again.");
    }
  };

  const clearChat = () => {
    setMessages([
      {
        role: "ai",
        content:
          "Chat cleared. Ask me about CRM priorities, customers, risks, opportunities, signals, actions, imports, or executive summaries.",
        meta: "New session",
      },
    ]);
  };

  const getModeLabel = (mode) => {
    const labels = {
      operator: "CRM Operator",
      executive: "Executive Brief",
      sales: "Sales Copilot",
      risk: "Risk Analyst",
    };

    return labels[mode] || "CRM Copilot";
  };

  const getModeBadgeClass = (mode) => {
    if (mode === "executive") return "badge badge-purple";
    if (mode === "sales") return "badge badge-green";
    if (mode === "risk") return "badge badge-red";
    return "badge badge-blue";
  };

  const renderFormattedMessage = (content, role) => {
    if (role === "user") {
      return <div className="message-bubble-user">{content}</div>;
    }

    const lines = String(content || "")
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);

    if (lines.length === 0) {
      return <p className="message-paragraph">No response.</p>;
    }

    const elements = [];
    let bulletBuffer = [];
    let numberBuffer = [];

    const flushBullets = () => {
      if (bulletBuffer.length > 0) {
        elements.push(
          <ul key={`bullets-${elements.length}`}>
            {bulletBuffer.map((item, index) => (
              <li key={index}>{formatInlineText(item)}</li>
            ))}
          </ul>
        );
        bulletBuffer = [];
      }
    };

    const flushNumbers = () => {
      if (numberBuffer.length > 0) {
        elements.push(
          <ol key={`numbers-${elements.length}`}>
            {numberBuffer.map((item, index) => (
              <li key={index}>{formatInlineText(item)}</li>
            ))}
          </ol>
        );
        numberBuffer = [];
      }
    };

    lines.forEach((line) => {
      const isBullet = /^[-*]\s+/.test(line);
      const isNumbered = /^\d+\.\s+/.test(line);
      const isHeading =
        line.endsWith(":") &&
        line.length < 90 &&
        !isBullet &&
        !isNumbered;

      if (isBullet) {
        flushNumbers();
        bulletBuffer.push(line.replace(/^[-*]\s+/, ""));
        return;
      }

      if (isNumbered) {
        flushBullets();
        numberBuffer.push(line.replace(/^\d+\.\s+/, ""));
        return;
      }

      flushBullets();
      flushNumbers();

      if (isHeading) {
        elements.push(
          <div key={`heading-${elements.length}`} className="message-heading">
            {line}
          </div>
        );
      } else {
        elements.push(
          <p key={`paragraph-${elements.length}`} className="message-paragraph">
            {formatInlineText(line)}
          </p>
        );
      }
    });

    flushBullets();
    flushNumbers();

    return <div className="message-bubble-ai">{elements}</div>;
  };

  const formatInlineText = (text) => {
    const parts = String(text).split(/(\*\*[^*]+\*\*)/g);

    return parts.map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      }

      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="page">
      <section className="page-hero">
        <div>
          <p className="page-eyebrow">CRM Copilot</p>
          <h1 className="page-title">AI Assistant</h1>
          <p className="page-subtitle">
            Ask business questions across customers, orders, signals, AI
            actions, imports, recommendations, and executive summaries. The
            copilot uses your CRM tools instead of acting like a generic chatbot.
          </p>
        </div>

        <div className="hero-actions">
          <button className="btn btn-secondary" onClick={clearChat}>
            Clear Chat
          </button>

          <button
            className="btn btn-primary"
            onClick={() =>
              handleQuickPrompt(
                "Give me an executive brief for the CRM business."
              )
            }
            disabled={loading}
          >
            Generate Executive Brief
          </button>
        </div>
      </section>

      <section className="grid-4">
        <div className="metric-card">
          <p className="metric-label">Copilot Mode</p>
          <p className="metric-value" style={{ fontSize: 24 }}>
            {getModeLabel(copilotMode)}
          </p>
          <p className="metric-meta">Response style and business focus</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">CRM Scope</p>
          <p className="metric-value" style={{ fontSize: 24 }}>
            Full Data
          </p>
          <p className="metric-meta">Customers, orders, signals, actions</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Tool-Based</p>
          <p className="metric-value" style={{ fontSize: 24 }}>
            Yes
          </p>
          <p className="metric-meta">Uses backend CRM tools</p>
        </div>

        <div className="metric-card">
          <p className="metric-label">Voice Input</p>
          <p className="metric-value" style={{ fontSize: 24 }}>
            {voiceSupported ? "Ready" : "Unavailable"}
          </p>
          <p className="metric-meta">Browser speech recognition</p>
        </div>
      </section>

      <section className="grid-2">
        <div className="stack">
          <section className="card">
            <div className="section-head">
              <div>
                <p className="section-eyebrow">Mode</p>
                <h2 className="section-title">Choose Copilot Focus</h2>
                <p className="section-description">
                  Change the assistant behavior based on the type of business
                  answer you need.
                </p>
              </div>
            </div>

            <div className="btn-row">
              <button
                className={
                  copilotMode === "operator"
                    ? "btn btn-primary"
                    : "btn btn-secondary"
                }
                onClick={() => setCopilotMode("operator")}
              >
                CRM Operator
              </button>

              <button
                className={
                  copilotMode === "executive"
                    ? "btn btn-primary"
                    : "btn btn-secondary"
                }
                onClick={() => setCopilotMode("executive")}
              >
                Executive
              </button>

              <button
                className={
                  copilotMode === "sales"
                    ? "btn btn-primary"
                    : "btn btn-secondary"
                }
                onClick={() => setCopilotMode("sales")}
              >
                Sales
              </button>

              <button
                className={
                  copilotMode === "risk"
                    ? "btn btn-primary"
                    : "btn btn-secondary"
                }
                onClick={() => setCopilotMode("risk")}
              >
                Risk
              </button>
            </div>
          </section>

          <section className="card">
            <div className="section-head">
              <div>
                <p className="section-eyebrow">Quick Actions</p>
                <h2 className="section-title">Ask High-Value Questions</h2>
              </div>
            </div>

            <div className="grid-2">
              {QUICK_PROMPTS.map((item) => (
                <button
                  key={item.label}
                  className="summary-box"
                  style={{
                    textAlign: "left",
                    cursor: loading ? "not-allowed" : "pointer",
                  }}
                  onClick={() => handleQuickPrompt(item.prompt)}
                  disabled={loading}
                >
                  <p className="summary-text">
                    <strong>{item.label}</strong>
                  </p>
                  <p className="summary-note">{item.description}</p>
                </button>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="section-head">
              <div>
                <p className="section-eyebrow">Examples</p>
                <h2 className="section-title">Question Ideas</h2>
              </div>
            </div>

            <div className="list">
              {EXAMPLE_QUESTIONS.map((question) => (
                <button
                  key={question}
                  className="list-row-compact"
                  style={{ textAlign: "left" }}
                  onClick={() => handleExampleClick(question)}
                >
                  <p className="list-title">{question}</p>
                </button>
              ))}
            </div>
          </section>
        </div>

        <section className="card chat-panel">
          <div className="section-head">
            <div>
              <p className="section-eyebrow">Conversation</p>
              <h2 className="section-title">CRM Copilot Chat</h2>
              <p className="section-description">
                Current mode:{" "}
                <span className={getModeBadgeClass(copilotMode)}>
                  {getModeLabel(copilotMode)}
                </span>
              </p>
            </div>
          </div>

          <div className="chat-window">
            {messages.map((message, index) => (
              <div
                key={index}
                className={
                  message.role === "user"
                    ? "message-row message-row-user"
                    : "message-row message-row-ai"
                }
              >
                <div className="message-meta">
                  <span
                    className={
                      message.role === "user"
                        ? "badge badge-blue"
                        : "badge badge-purple"
                    }
                  >
                    {message.role === "user" ? "You" : "AI Copilot"}
                  </span>

                  {message.meta && (
                    <span className="badge badge-yellow">{message.meta}</span>
                  )}
                </div>

                {renderFormattedMessage(message.content, message.role)}
              </div>
            ))}

            {loading && (
              <div className="message-row message-row-ai">
                <div className="message-meta">
                  <span className="badge badge-purple">AI Copilot</span>
                  <span className="badge badge-yellow">Thinking</span>
                </div>

                <div className="message-bubble-ai">
                  <p className="message-paragraph">
                    Analyzing CRM data and selecting the right tool...
                  </p>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-card">
            {voiceError && (
              <div className="error-state" style={{ marginBottom: 12 }}>
                {voiceError}
              </div>
            )}

            <textarea
              className="textarea"
              placeholder="Ask about customers, risks, opportunities, actions, imports, signals, or executive priorities..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={4}
            />

            <div className="results-bar" style={{ marginTop: 12 }}>
              <div className="btn-row">
                <button
                  className="btn btn-primary"
                  onClick={handleSend}
                  disabled={loading || !input.trim()}
                >
                  {loading ? "Thinking..." : "Send"}
                </button>

                <button
                  className="btn btn-secondary"
                  onClick={startVoiceInput}
                  disabled={!voiceSupported}
                >
                  {isListening ? "Stop Listening" : "Voice Input"}
                </button>
              </div>

              <p className="results-text">
                Press <strong>Enter</strong> to send ·{" "}
                <strong>Shift + Enter</strong> for new line
              </p>
            </div>
          </div>
        </section>
      </section>
    </div>
  );
}

export default AIChat;