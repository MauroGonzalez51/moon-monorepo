import { defineConfig } from "tsup";

export default defineConfig({
    entry: ["src/index.ts"],
    outDir: "dist",
    format: ["esm", "cjs"],
    dts: true,
    clean: true,
    sourcemap: true,
    outExtension({ format }) {
        if (format === "esm") {
            return {
                js: ".mjs",
                dts: ".d.mts",
            };
        }

        if (format === "cjs") {
            return {
                js: ".cjs",
                dts: ".d.cts",
            };
        }

        return {
            js: ".js",
            dts: ".d.ts",
        };
    },
});
