import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  SafeAreaView,
  StatusBar,
} from "react-native";
import * as WebBrowser from "expo-web-browser";
import { colors, fontSize, spacing } from "../lib/theme";
import { setToken, setStoredUser } from "../lib/api";

interface LoginScreenProps {
  onLogin: () => void;
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError(null);

    try {
      // Open Google OAuth via backend
      const result = await WebBrowser.openAuthSessionAsync(
        "https://hireai-backend.onrender.com/auth/google/mobile",
        "hireai://auth/callback"
      );

      if (result.type === "success" && result.url) {
        // Parse token from callback URL
        const url = new URL(result.url);
        const token = url.searchParams.get("token");
        const email = url.searchParams.get("email");
        const name = url.searchParams.get("name");

        if (token) {
          await setToken(token);
          await setStoredUser({ email, name });
          onLogin();
        } else {
          setError("Login failed — no token received");
        }
      }
    } catch (err) {
      setError("Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.navy} />
      <View style={styles.content}>
        {/* Logo */}
        <View style={styles.logo}>
          <Text style={styles.logoText}>H</Text>
        </View>
        <Text style={styles.title}>HireAI</Text>
        <Text style={styles.subtitle}>
          Your AI-powered email employee
        </Text>

        {/* Features */}
        <View style={styles.features}>
          {["Auto-reply to emails", "Smart email classification", "Calendar scheduling", "Contact management"].map((f) => (
            <View key={f} style={styles.featureRow}>
              <Text style={styles.featureCheck}>✓</Text>
              <Text style={styles.featureText}>{f}</Text>
            </View>
          ))}
        </View>

        {/* Login Button */}
        <TouchableOpacity
          style={styles.loginButton}
          onPress={handleGoogleLogin}
          disabled={loading}
          activeOpacity={0.8}
        >
          {loading ? (
            <ActivityIndicator color={colors.navy} />
          ) : (
            <Text style={styles.loginButtonText}>Sign in with Google</Text>
          )}
        </TouchableOpacity>

        {error && <Text style={styles.error}>{error}</Text>}

        <Text style={styles.footer}>
          By signing in, you agree to our Terms & Privacy Policy
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.navy,
  },
  content: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xl,
  },
  logo: {
    width: 80,
    height: 80,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  logoText: {
    fontSize: 36,
    fontWeight: "700",
    color: colors.white,
  },
  title: {
    fontSize: fontSize.xxl,
    fontWeight: "700",
    color: colors.white,
    marginBottom: spacing.xs,
  },
  subtitle: {
    fontSize: fontSize.md,
    color: "rgba(255,255,255,0.7)",
    marginBottom: spacing.xl,
  },
  features: {
    alignSelf: "stretch",
    marginBottom: spacing.xl,
  },
  featureRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  featureCheck: {
    fontSize: fontSize.md,
    color: "#4ADE80",
    marginRight: spacing.sm,
    fontWeight: "600",
  },
  featureText: {
    fontSize: fontSize.md,
    color: "rgba(255,255,255,0.9)",
  },
  loginButton: {
    alignSelf: "stretch",
    backgroundColor: colors.white,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
    marginBottom: spacing.md,
  },
  loginButtonText: {
    fontSize: fontSize.md,
    fontWeight: "600",
    color: colors.navy,
  },
  error: {
    color: "#FCA5A5",
    fontSize: fontSize.sm,
    marginBottom: spacing.sm,
  },
  footer: {
    fontSize: fontSize.xs,
    color: "rgba(255,255,255,0.5)",
    textAlign: "center",
    marginTop: spacing.md,
  },
});
