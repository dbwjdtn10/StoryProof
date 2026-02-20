
import { createRoot } from "react-dom/client";
import { Toaster } from "sonner";
import App from "./App.tsx";
import { ThemeProvider } from "./contexts/ThemeContext.tsx";
import "./index.css";
import "./login.css";
import "./upload.css";
import "./chapter-detail.css";
import "./floating-menu.css";
import "./theme.css";
import "./splash-screen.css";

createRoot(document.getElementById("root")!).render(
    <ThemeProvider>
        <App />
        <Toaster position="top-right" richColors />
    </ThemeProvider>
);
