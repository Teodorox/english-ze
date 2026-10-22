import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { initTheme } from "./lib/theme";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/layout.css";
import "./styles/zeicon.css";
import "./styles/login.css";
import "./styles/onboarding.css";
import "./styles/study.css";
import "./styles/speak.css";
import "./styles/mine.css";
import "./styles/vault.css";
import "./styles/journal.css";
import "./styles/stats.css";
import "./styles/today.css";
import "./styles/desktop.css"; // por último: só vale em telas largas

initTheme();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
