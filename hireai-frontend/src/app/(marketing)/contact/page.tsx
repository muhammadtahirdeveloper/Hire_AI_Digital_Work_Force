"use client";

import { useState } from "react";
import {
  Mail,
  Clock,
  Send,
  MessageSquare,
  MapPin,
  CheckCircle,
} from "lucide-react";
import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Footer } from "@/components/marketing/landing/footer";

export default function ContactPage() {
  const [formState, setFormState] = useState({
    name: "",
    email: "",
    message: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    // Simulate sending — replace with real API call
    setTimeout(() => {
      setSending(false);
      setSubmitted(true);
      setFormState({ name: "", email: "", message: "" });
    }, 1000);
  }

  return (
    <>
      <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
            Contact Us
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg text-text-3">
            Have a question, feedback, or need help? We&apos;d love to hear from
            you.
          </p>
        </div>

        <div className="mt-12 grid gap-8 lg:grid-cols-5">
          {/* Contact Info Cards */}
          <div className="space-y-4 lg:col-span-2">
            <Card>
              <CardBody className="flex items-start gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy/10">
                  <Mail className="h-5 w-5 text-navy" />
                </div>
                <div>
                  <h3 className="font-semibold text-text">Email</h3>
                  <a
                    href="mailto:hireaidigitalemployee@gmail.com"
                    className="mt-1 block text-sm text-navy hover:underline"
                  >
                    hireaidigitalemployee@gmail.com
                  </a>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardBody className="flex items-start gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy/10">
                  <Clock className="h-5 w-5 text-navy" />
                </div>
                <div>
                  <h3 className="font-semibold text-text">Response Time</h3>
                  <p className="mt-1 text-sm text-text-3">
                    We typically respond within 24 hours on business days.
                  </p>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardBody className="flex items-start gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy/10">
                  <MessageSquare className="h-5 w-5 text-navy" />
                </div>
                <div>
                  <h3 className="font-semibold text-text">Live Chat</h3>
                  <p className="mt-1 text-sm text-text-3">
                    Use the AI chatbot on any page for instant help 24/7.
                  </p>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardBody className="flex items-start gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy/10">
                  <MapPin className="h-5 w-5 text-navy" />
                </div>
                <div>
                  <h3 className="font-semibold text-text">Location</h3>
                  <p className="mt-1 text-sm text-text-3">
                    Remote-first company serving businesses worldwide.
                  </p>
                </div>
              </CardBody>
            </Card>
          </div>

          {/* Contact Form */}
          <div className="lg:col-span-3">
            <Card>
              <CardBody className="p-6 sm:p-8">
                {submitted ? (
                  <div className="flex flex-col items-center py-12 text-center">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-success/10">
                      <CheckCircle className="h-8 w-8 text-success" />
                    </div>
                    <h3 className="mt-4 text-xl font-bold text-text">
                      Message Sent!
                    </h3>
                    <p className="mt-2 text-sm text-text-3">
                      Thank you for reaching out. We&apos;ll get back to you
                      within 24 hours.
                    </p>
                    <Button
                      variant="outline"
                      className="mt-6"
                      onClick={() => setSubmitted(false)}
                    >
                      Send Another Message
                    </Button>
                  </div>
                ) : (
                  <>
                    <h2 className="text-lg font-bold text-text">
                      Send us a message
                    </h2>
                    <p className="mt-1 text-sm text-text-3">
                      Fill out the form below and we&apos;ll get back to you as
                      soon as possible.
                    </p>

                    <form onSubmit={handleSubmit} className="mt-6 space-y-5">
                      {/* Name */}
                      <div>
                        <label
                          htmlFor="name"
                          className="block text-sm font-medium text-text"
                        >
                          Full Name
                        </label>
                        <input
                          id="name"
                          type="text"
                          required
                          value={formState.name}
                          onChange={(e) =>
                            setFormState((s) => ({
                              ...s,
                              name: e.target.value,
                            }))
                          }
                          className="mt-1.5 w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-text placeholder:text-text-4 focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy"
                          placeholder="Your name"
                        />
                      </div>

                      {/* Email */}
                      <div>
                        <label
                          htmlFor="email"
                          className="block text-sm font-medium text-text"
                        >
                          Email Address
                        </label>
                        <input
                          id="email"
                          type="email"
                          required
                          value={formState.email}
                          onChange={(e) =>
                            setFormState((s) => ({
                              ...s,
                              email: e.target.value,
                            }))
                          }
                          className="mt-1.5 w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-text placeholder:text-text-4 focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy"
                          placeholder="you@example.com"
                        />
                      </div>

                      {/* Message */}
                      <div>
                        <label
                          htmlFor="message"
                          className="block text-sm font-medium text-text"
                        >
                          Message
                        </label>
                        <textarea
                          id="message"
                          required
                          rows={5}
                          value={formState.message}
                          onChange={(e) =>
                            setFormState((s) => ({
                              ...s,
                              message: e.target.value,
                            }))
                          }
                          className="mt-1.5 w-full resize-none rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-text placeholder:text-text-4 focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy"
                          placeholder="How can we help you?"
                        />
                      </div>

                      <Button
                        type="submit"
                        className="w-full"
                        disabled={sending}
                      >
                        {sending ? (
                          "Sending..."
                        ) : (
                          <>
                            <Send className="mr-2 h-4 w-4" />
                            Send Message
                          </>
                        )}
                      </Button>
                    </form>
                  </>
                )}
              </CardBody>
            </Card>
          </div>
        </div>
      </div>
      <Footer />
    </>
  );
}
