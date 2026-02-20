
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import { ThemeProvider } from "./contexts/ThemeContext.tsx";
import "./index.css";
import "./login.css";
import "./upload.css";
import "./chapter-detail.css";
import "./floating-menu.css";
import "./theme.css";

createRoot(document.getElementById("root")!).render(
    <ThemeProvider>
        <App />
    </ThemeProvider>
);
