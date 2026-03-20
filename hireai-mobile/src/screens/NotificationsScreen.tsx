import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, fontSize, spacing } from "../lib/theme";
import { api } from "../lib/api";
import { registerForPushNotifications } from "../lib/notifications";

interface NotificationItem {
  id: string;
  title: string;
  body: string;
  type: "escalation" | "new_lead" | "daily_summary" | "agent_error" | "info";
  read: boolean;
  created_at: string;
}

export default function NotificationsScreen() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [pushEnabled, setPushEnabled] = useState(false);

  const fetchNotifications = useCallback(async () => {
    // Fetch escalated emails as notification-like items
    const res = await api.get<Array<Record<string, unknown>>>("/api/emails/recent?action=escalated&limit=20");
    if (res.data && Array.isArray(res.data)) {
      const items: NotificationItem[] = res.data.map((e: Record<string, unknown>) => ({
        id: String(e.id || Math.random()),
        title: "Urgent Email Escalated",
        body: `From ${e.from_name || e.from}: ${e.subject}`,
        type: "escalation" as const,
        read: false,
        created_at: String(e.timestamp || new Date().toISOString()),
      }));
      setNotifications(items);
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchNotifications(); }, [fetchNotifications]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchNotifications();
    setRefreshing(false);
  };

  const enablePush = async () => {
    const token = await registerForPushNotifications();
    if (token) {
      setPushEnabled(true);
    }
  };

  const typeIcon = (type: string) => {
    switch (type) {
      case "escalation": return { emoji: "⚠️", color: colors.warningLight };
      case "new_lead": return { emoji: "🎯", color: colors.successLight };
      case "agent_error": return { emoji: "❌", color: colors.dangerLight };
      case "daily_summary": return { emoji: "📊", color: colors.navyLight };
      default: return { emoji: "ℹ️", color: colors.navyLight };
    }
  };

  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      const now = new Date();
      const diff = now.getTime() - d.getTime();
      if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
      if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
      return d.toLocaleDateString();
    } catch {
      return "";
    }
  };

  const renderItem = ({ item }: { item: NotificationItem }) => {
    const { emoji, color } = typeIcon(item.type);
    return (
      <View style={styles.notifCard}>
        <View style={[styles.notifIcon, { backgroundColor: color }]}>
          <Text style={{ fontSize: 18 }}>{emoji}</Text>
        </View>
        <View style={{ flex: 1 }}>
          <View style={styles.notifHeader}>
            <Text style={styles.notifTitle}>{item.title}</Text>
            <Text style={styles.notifTime}>{formatTime(item.created_at)}</Text>
          </View>
          <Text style={styles.notifBody} numberOfLines={2}>{item.body}</Text>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <Text style={styles.title}>Notifications</Text>

      {/* Push Enable Banner */}
      {!pushEnabled && (
        <TouchableOpacity style={styles.pushBanner} onPress={enablePush} activeOpacity={0.8}>
          <Text style={styles.pushBannerText}>
            🔔 Enable push notifications for urgent emails
          </Text>
          <Text style={styles.pushBannerAction}>Enable</Text>
        </TouchableOpacity>
      )}

      {loading ? (
        <ActivityIndicator size="large" color={colors.navy} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={notifications}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.navy} />}
          contentContainerStyle={{ paddingHorizontal: spacing.md, paddingBottom: 100 }}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emptyEmoji}>🎉</Text>
              <Text style={styles.emptyTitle}>All Clear!</Text>
              <Text style={styles.emptyText}>No urgent notifications right now</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  title: { fontSize: fontSize.xl, fontWeight: "700", color: colors.text, paddingHorizontal: spacing.md, marginBottom: spacing.sm },
  pushBanner: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.navyLight,
    marginHorizontal: spacing.md,
    marginBottom: spacing.md,
    padding: spacing.md,
    borderRadius: 12,
  },
  pushBannerText: { fontSize: fontSize.sm, color: colors.navy, flex: 1 },
  pushBannerAction: { fontSize: fontSize.sm, fontWeight: "700", color: colors.navy, marginLeft: spacing.sm },
  notifCard: {
    flexDirection: "row",
    backgroundColor: colors.backgroundCard,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  notifIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    marginRight: spacing.sm,
  },
  notifHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  notifTitle: { fontSize: fontSize.sm, fontWeight: "600", color: colors.text, flex: 1 },
  notifTime: { fontSize: fontSize.xs, color: colors.textMuted },
  notifBody: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2 },
  empty: { alignItems: "center", paddingVertical: 60 },
  emptyEmoji: { fontSize: 48, marginBottom: spacing.md },
  emptyTitle: { fontSize: fontSize.lg, fontWeight: "600", color: colors.text },
  emptyText: { fontSize: fontSize.sm, color: colors.textMuted, marginTop: 4 },
});
