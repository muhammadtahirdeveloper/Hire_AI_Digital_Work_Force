"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { Star, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import toast from "react-hot-toast";

const featureLabels = [
  { key: "classification", label: "Email Classification" },
  { key: "autoReply", label: "Auto-Reply Quality" },
  { key: "dashboard", label: "Dashboard & Analytics" },
  { key: "setup", label: "Ease of Setup" },
  { key: "support", label: "Customer Support" },
];

interface ReviewModalProps {
  open: boolean;
  onClose: () => void;
}

export function ReviewModal({ open, onClose }: ReviewModalProps) {
  const { data: session } = useSession();
  const [step, setStep] = useState(1);
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [reviewText, setReviewText] = useState("");
  const [featureRatings, setFeatureRatings] = useState<Record<string, number>>({});
  const [role, setRole] = useState("");
  const [company, setCompany] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await api.post("/api/reviews", {
        user_id: session?.user?.id,
        user_name: session?.user?.name,
        user_email: session?.user?.email,
        user_role: role || null,
        user_company: company || null,
        rating,
        review_text: reviewText || null,
        feature_ratings: Object.keys(featureRatings).length > 0 ? featureRatings : null,
        is_public: isPublic,
        agent_type: session?.user?.agentType,
        tier: session?.user?.tier,
      });
      toast.success("Thank you for your review!");
      onClose();
    } catch {
      toast.error("Failed to submit review");
    }
    setSubmitting(false);
  };

  const handleSkip = () => {
    onClose();
  };

  const renderStars = (
    currentRating: number,
    onSelect: (val: number) => void,
    size: "lg" | "sm" = "lg",
    hover?: number,
    onHover?: (val: number) => void
  ) => {
    const starSize = size === "lg" ? "h-8 w-8" : "h-5 w-5";
    return (
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((i) => (
          <button
            key={i}
            onClick={() => onSelect(i)}
            onMouseEnter={() => onHover?.(i)}
            onMouseLeave={() => onHover?.(0)}
            className="transition-transform hover:scale-110"
          >
            <Star
              className={cn(
                starSize,
                "transition-colors",
                i <= (hover || currentRating)
                  ? "fill-amber-400 text-amber-400"
                  : "text-border-2"
              )}
            />
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={handleSkip} />

      {/* Modal */}
      <div className="relative w-full max-w-md rounded-xl border border-border bg-background p-6 shadow-xl">
        {/* Close button */}
        <button
          onClick={handleSkip}
          className="absolute right-4 top-4 rounded-sm text-text-4 hover:text-text"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Step indicator */}
        <div className="mb-6 flex gap-1">
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              className={cn(
                "h-1 flex-1 rounded-full transition-colors",
                s <= step ? "bg-navy" : "bg-background-2"
              )}
            />
          ))}
        </div>

        {/* Step 1: Star Rating */}
        {step === 1 && (
          <div className="text-center">
            <h2 className="text-xl font-bold text-text">
              How would you rate HireAI?
            </h2>
            <p className="mt-1 text-sm text-text-3">
              Your feedback helps us improve
            </p>
            <div className="mt-8 flex justify-center">
              {renderStars(rating, setRating, "lg", hoverRating, setHoverRating)}
            </div>
            {rating > 0 && (
              <p className="mt-3 text-sm text-text-2">
                {rating === 5
                  ? "Excellent!"
                  : rating === 4
                    ? "Great!"
                    : rating === 3
                      ? "Good"
                      : rating === 2
                        ? "Fair"
                        : "Needs improvement"}
              </p>
            )}
          </div>
        )}

        {/* Step 2: Written Review */}
        {step === 2 && (
          <div>
            <h2 className="text-xl font-bold text-text">
              Tell us about your experience
            </h2>
            <p className="mt-1 text-sm text-text-3">Optional but appreciated</p>
            <textarea
              className="mt-4 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-text placeholder:text-text-4 focus:outline-none focus:ring-2 focus:ring-navy"
              rows={4}
              placeholder="What has HireAI helped you with most?"
              value={reviewText}
              onChange={(e) => setReviewText(e.target.value)}
            />
            {reviewText.length > 0 && reviewText.length < 20 && (
              <p className="mt-1 text-xs text-warning">
                Minimum 20 characters ({20 - reviewText.length} more)
              </p>
            )}
          </div>
        )}

        {/* Step 3: Feature Ratings */}
        {step === 3 && (
          <div>
            <h2 className="text-xl font-bold text-text">Rate our features</h2>
            <p className="mt-1 text-sm text-text-3">Optional — skip any</p>
            <div className="mt-4 space-y-4">
              {featureLabels.map((f) => (
                <div
                  key={f.key}
                  className="flex items-center justify-between"
                >
                  <span className="text-sm text-text-2">{f.label}</span>
                  {renderStars(
                    featureRatings[f.key] || 0,
                    (val) =>
                      setFeatureRatings((prev) => ({ ...prev, [f.key]: val })),
                    "sm"
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 4: Profile Info */}
        {step === 4 && (
          <div>
            <h2 className="text-xl font-bold text-text">Almost done!</h2>
            <p className="mt-1 text-sm text-text-3">
              Help others by sharing your role
            </p>
            <div className="mt-4 space-y-4">
              <Input
                label="Your role / title"
                placeholder="e.g., HR Manager"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              />
              <Input
                label="Company name (optional)"
                placeholder="e.g., Acme Corp"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
              />
              <Switch
                checked={isPublic}
                onCheckedChange={setIsPublic}
                label="Make my review public"
              />
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="mt-8 flex items-center justify-between">
          <button
            onClick={handleSkip}
            className="text-xs text-text-4 hover:text-text-3"
          >
            Maybe later
          </button>

          <div className="flex gap-2">
            {step > 1 && (
              <Button variant="ghost" size="sm" onClick={() => setStep((s) => s - 1)}>
                Back
              </Button>
            )}
            {step < 4 ? (
              <Button
                size="sm"
                disabled={step === 1 && rating === 0}
                onClick={() => setStep((s) => s + 1)}
              >
                {step === 2 && !reviewText ? "Skip" : "Next"}
              </Button>
            ) : (
              <Button size="sm" loading={submitting} onClick={handleSubmit}>
                Submit Review
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
