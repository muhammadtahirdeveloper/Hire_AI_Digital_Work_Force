import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Switch,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, fontSize, spacing } from "../lib/theme";
import { api, removeToken } from "../lib/api";

interface AgentConfig {
  is_paused: boolean;
  test_mode: boolean;
  auto_send_enabled: boolean;
  daily_limit: number;
  provider: string;
  model: string;
  tier: string;
  gmail_email: string;
}

interface SettingsScreenProps {
  onLogout: () => void;
}

export default function SettingsScreen({ onLogout }: SettingsScreenProps) {
  const [config, setConfig] = useState<AgentConfig | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchConfig = useCallback(async () => {
    const res = await api.get<AgentConfig>("/api/agent/status");
    if (res.data) setConfig(res.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const toggleSetting = async (key: string, endpoint: string) => {
    if (!config) return;
    const current = (config as unknown as Record<string, unknown>)[key] as boolean;
    try {
      if (key === "is_paused") {
        await api.post(`/api/agent/${current ? "resume" : "pause"}`);
      } else if (key === "test_mode") {
        await api.post("/api/agent/test-mode", { enabled: !current });
      } else if (key === "auto_send_enabled") {
        await api.post("/api/agent/auto-send", { enabled: !current });
      }
      fetchConfig();
    } catch {
      Alert.alert("Error", "Failed to update setting");
    }
  };

  const handleLogout = () => {
    Alert.alert("Sign Out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        style: "destructive",
        onPress: async () => {
          await removeToken();
          onLogout();
        },
      },
    ]);
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.navy} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Settings</Text>

        {/* Account Info */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Account</Text>
          <View style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.label}>Gmail</Text>
              <Text style={styles.value}>{config?.gmail_email ?? "Not connected"}</Text>
            </View>
            <View style={styles.divider} />
            <View style={styles.row}>
              <Text style={styles.label}>Plan</Text>
              <View style={styles.tierBadge}>
                <Text style={styles.tierText}>{config?.tier ?? "trial"}</Text>
              </View>
            </View>
            <View style={styles.divider} />
            <View style={styles.row}>
              <Text style={styles.label}>AI Provider</Text>
              <Text style={styles.value}>{config?.provider ?? "groq"} / {config?.model ?? "auto"}</Text>
            </View>
            <View style={styles.divider} />
            <View style={styles.row}>
              <Text style={styles.label}>Daily Limit</Text>
              <Text style={styles.value}>{config?.daily_limit ?? 100}</Text>
            </View>
          </View>
        </View>

        {/* Agent Controls */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Agent Controls</Text>
          <View style={styles.card}>
            <View style={styles.row}>
              <View>
                <Text style={styles.label}>Agent Active</Text>
                <Text style={styles.hint}>Process incoming emails automatically</Text>
              </View>
              <Switch
                value={!config?.is_paused}
                onValueChange={() => toggleSetting("is_paused", "")}
                trackColor={{ true: colors.success, false: colors.border }}
                thumbColor={colors.white}
              />
            </View>
            <View style={styles.divider} />
            <View style={styles.row}>
              <View>
                <Text style={styles.label}>Test Mode</Text>
                <Text style={styles.hint}>Creates drafts instead of sending</Text>
              </View>
              <Switch
                value={config?.test_mode ?? false}
                onValueChange={() => toggleSetting("test_mode", "")}
                trackColor={{ true: colors.warning, false: colors.border }}
                thumbColor={colors.white}
              />
            </View>
            <View style={styles.divider} />
            <View style={styles.row}>
              <View>
                <Text style={styles.label}>Auto-Send</Text>
                <Text style={styles.hint}>Send replies without review</Text>
              </View>
              <Switch
                value={config?.auto_send_enabled ?? false}
                onValueChange={() => toggleSetting("auto_send_enabled", "")}
                trackColor={{ true: colors.navy, false: colors.border }}
                thumbColor={colors.white}
              />
            </View>
          </View>
        </View>

        {/* Logout */}
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout} activeOpacity={0.8}>
          <Text style={styles.logoutText}>Sign Out</Text>
        </TouchableOpacity>

        <Text style={styles.version}>HireAI Mobile v1.0.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  loadingContainer: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background },
  scroll: { padding: spacing.md, paddingBottom: 100 },
  title: { fontSize: fontSize.xl, fontWeight: "700", color: colors.text, marginBottom: spacing.lg },
  section: { marginBottom: spacing.lg },
  sectionTitle: { fontSize: fontSize.sm, fontWeight: "600", color: colors.textMuted, marginBottom: spacing.sm, textTransform: "uppercase", letterSpacing: 0.5 },
  card: {
    backgroundColor: colors.backgroundCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: 14,
  },
  divider: { height: 1, backgroundColor: colors.border },
  label: { fontSize: fontSize.md, fontWeight: "500", color: colors.text },
  value: { fontSize: fontSize.sm, color: colors.textSecondary },
  hint: { fontSize: fontSize.xs, color: colors.textMuted, marginTop: 2, maxWidth: 200 },
  tierBadge: { backgroundColor: colors.navyLight, paddingHorizontal: 10, paddingVertical: 3, borderRadius: 6 },
  tierText: { fontSize: fontSize.xs, fontWeight: "600", color: colors.navy, textTransform: "capitalize" },
  logoutButton: {
    backgroundColor: colors.dangerLight,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: spacing.md,
  },
  logoutText: { fontSize: fontSize.md, fontWeight: "600", color: colors.danger },
  version: { fontSize: fontSize.xs, color: colors.textMuted, textAlign: "center", marginTop: spacing.lg },
});
