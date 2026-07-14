import type { OptionsConfig, Rules, TypedFlatConfigItem } from "@antfu/eslint-config";
import { antfu } from "@antfu/eslint-config";
import { merge } from "es-toolkit/compat";
import depend from "eslint-plugin-depend";

interface PluginDefinition {
    plugin: unknown;
    rules: Partial<Rules> | undefined;
}

const PluginsRecord: Record<string, PluginDefinition> = {
    depend: {
        plugin: depend,
        rules: {
            "depend/ban-dependencies": "error",
        },
    },
};

type DeclaredPluginsConfig = {
    [K in keyof typeof PluginsRecord]?: {
        enabled?: boolean;
        rules?: Partial<Rules>;
    };
};

export function withConfig(
    config?: OptionsConfig & Omit<TypedFlatConfigItem, "files" | "ignores">,
    plugins: DeclaredPluginsConfig = {},
): ReturnType<typeof antfu> {
    const pluginConfigs = Object.entries(PluginsRecord).map(([name, value]) => {
        const override = plugins[name as keyof typeof PluginsRecord];

        return {
            name,
            plugin: value.plugin,
            enabled: override?.enabled ?? true,
            rules: {
                ...value.rules,
                ...override?.rules,
            },
        };
    });

    const { activePlugins, activeRules } = pluginConfigs
        .filter((plugin) => plugin.enabled)
        .reduce(
            (acc, plugin) => {
                acc.activePlugins[plugin.name] = plugin.plugin;
                Object.assign(acc.activeRules, plugin.rules);

                return acc;
            },
            {
                activePlugins: {} as Record<string, unknown>,
                activeRules: {} as Partial<Rules>,
            },
        );

    const defaultConfig: OptionsConfig & Omit<TypedFlatConfigItem, "files" | "ignores"> = {
        stylistic: {
            quotes: "double",
            indent: 4,
            semi: true,
        },
        rules: {
            "yaml/indent": ["warn", 4, { indicatorValueIndent: 2 }],
            "style/arrow-parens": ["warn", "always"],
            "style/operator-linebreak": ["off"],
            "style/brace-style": ["warn", "1tbs"],
            "style/quote-props": ["error", "as-needed"],
        },
    };

    return antfu(merge({}, defaultConfig, config), {
        plugins: activePlugins,
        rules: activeRules,
    });
}
