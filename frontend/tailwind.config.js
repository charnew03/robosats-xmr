export default {
    content: ["./index.html", "./src/**/*.{ts,tsx}"],
    theme: {
        extend: {
            colors: {
                xmr: {
                    bg: "#09090b",
                    panel: "#111216",
                    border: "#252833",
                    accent: "#ff7a00",
                    accentSoft: "#ff9d47",
                    text: "#f4f4f5",
                    muted: "#9ca3af",
                },
            },
        },
    },
    darkMode: "class",
    plugins: [],
};
