import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  RefreshControl,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, fontSize, spacing } from "../lib/theme";
import { api } from "../lib/api";

interface EmailEntry {
  id: string;
  from: string;
  from_name: string;
  subject: string;
  category: string;
  action: string;
  timestamp: string;
}

const ACTION_FILTERS = ["all", "auto_replied", "draft_created", "escalated", "blocked"];

export default function EmailsScreen() {
  const [emails, setEmails] = useState<EmailEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const fetchEmails = useCallback(async (pageNum = 1, reset = false) => {
    const actionParam = filter !== "all" ? `&action=${filter}` : "";
    const searchParam = search ? `&search=${encodeURIComponent(search)}` : "";
    const res = await api.get<{ emails: EmailEntry[]; total: number }>(
      `/api/emails/log?page=${pageNum}&per_page=20${actionParam}${searchParam}`
    );

    if (res.data) {
      const newEmails = (res.data as any).emails ?? (Array.isArray(res.data) ? res.data : []);
      setEmails(reset ? newEmails : [...emails, ...newEmails]);
      setHasMore(newEmails.length === 20);
    }
    setLoading(false);
  }, [filter, search]);

  useEffect(() => {
    setLoading(true);
    setPage(1);
    fetchEmails(1, true);
  }, [filter, search]);

  const onRefresh = async () => {
    setRefreshing(true);
    setPage(1);
    await fetchEmails(1, true);
    setRefreshing(false);
  };

  const loadMore = () => {
    if (!hasMore || loading) return;
    const nextPage = page + 1;
    setPage(nextPage);
    fetchEmails(nextPage);
  };

  const actionColor = (action: string) => {
    switch (action) {
      case "auto_replied": return colors.success;
      case "draft_created": return colors.navy;
      case "escalated": return colors.warning;
      case "blocked": return colors.danger;
      default: return colors.textMuted;
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
      return ts;
    }
  };

  const renderEmail = ({ item }: { item: EmailEntry }) => (
    <View style={styles.emailCard}>
      <View style={styles.emailRow}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {(item.from_name || item.from || "?")[0].toUpperCase()}
          </Text>
        </View>
        <View style={{ flex: 1 }}>
          <View style={styles.emailTop}>
            <Text style={styles.sender} numberOfLines={1}>
              {item.from_name || item.from}
            </Text>
            <Text style={styles.time}>{formatTime(item.timestamp)}</Text>
          </View>
          <Text style={styles.subject} numberOfLines={1}>{item.subject}</Text>
          <View style={styles.tagsRow}>
            <View style={[styles.badge, { backgroundColor: colors.navyLight }]}>
              <Text style={[styles.badgeText, { color: colors.navy }]}>{item.category}</Text>
            </View>
            <View style={[styles.badge, { backgroundColor: actionColor(item.action) + "20" }]}>
              <Text style={[styles.badgeText, { color: actionColor(item.action) }]}>
                {item.action.replace("_", " ")}
              </Text>
            </View>
          </View>
        </View>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <Text style={styles.title}>Email Log</Text>

      {/* Search */}
      <View style={styles.searchBox}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search emails..."
          placeholderTextColor={colors.textMuted}
          value={search}
          onChangeText={setSearch}
        />
      </View>

      {/* Filters */}
      <FlatList
        horizontal
        data={ACTION_FILTERS}
        keyExtractor={(item) => item}
        showsHorizontalScrollIndicator={false}
        style={styles.filterList}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.filterChip, filter === item && styles.filterChipActive]}
            onPress={() => setFilter(item)}
            activeOpacity={0.7}
          >
            <Text style={[styles.filterText, filter === item && styles.filterTextActive]}>
              {item === "all" ? "All" : item.replace("_", " ")}
            </Text>
          </TouchableOpacity>
        )}
      />

      {/* Email List */}
      {loading && page === 1 ? (
        <ActivityIndicator size="large" color={colors.navy} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={emails}
          keyExtractor={(item) => item.id}
          renderItem={renderEmail}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.navy} />}
          onEndReached={loadMore}
          onEndReachedThreshold={0.3}
          contentContainerStyle={{ paddingHorizontal: spacing.md, paddingBottom: 100 }}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emptyText}>No emails found</Text>
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
  searchBox: { paddingHorizontal: spacing.md, marginBottom: spacing.sm },
  searchInput: {
    backgroundColor: colors.backgroundCard,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: fontSize.sm,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.border,
  },
  filterList: { paddingHorizontal: spacing.md, marginBottom: spacing.sm, maxHeight: 40 },
  filterChip: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: colors.backgroundCard,
    marginRight: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  filterChipActive: { backgroundColor: colors.navy, borderColor: colors.navy },
  filterText: { fontSize: fontSize.xs, fontWeight: "500", color: colors.textSecondary, textTransform: "capitalize" },
  filterTextActive: { color: colors.white },
  emailCard: {
    backgroundColor: colors.backgroundCard,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  emailRow: { flexDirection: "row", alignItems: "flex-start" },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.navyLight,
    alignItems: "center",
    justifyContent: "center",
    marginRight: spacing.sm,
  },
  avatarText: { fontSize: fontSize.sm, fontWeight: "600", color: colors.navy },
  emailTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  sender: { fontSize: fontSize.sm, fontWeight: "600", color: colors.text, flex: 1 },
  time: { fontSize: fontSize.xs, color: colors.textMuted, marginLeft: spacing.sm },
  subject: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2, marginBottom: 6 },
  tagsRow: { flexDirection: "row", gap: 6 },
  badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6 },
  badgeText: { fontSize: 10, fontWeight: "600", textTransform: "capitalize" },
  empty: { alignItems: "center", paddingVertical: 40 },
  emptyText: { fontSize: fontSize.sm, color: colors.textMuted },
});
