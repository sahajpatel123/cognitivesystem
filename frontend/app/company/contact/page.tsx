"use client";

import { useState } from "react";
import { motion } from "framer-motion";

export default function ContactPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    topic: "General",
    message: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.name.trim()) newErrors.name = "Name is required";
    if (!formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Please enter a valid email";
    }
    if (!formData.message.trim()) newErrors.message = "Message is required";
    return newErrors;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors = validateForm();
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    setErrors({});
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      setIsSuccess(true);
      setTimeout(() => {
        setIsSuccess(false);
        setFormData({ name: "", email: "", topic: "General", message: "" });
      }, 3000);
    }, 1500);
  };

  const copyEmail = () => {
    navigator.clipboard.writeText("hello@cognitivesystem.ai");
    setCopiedEmail(true);
    setTimeout(() => setCopiedEmail(false), 2000);
  };

  return (
    <motion.div
      className="page-frame"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Hero Section */}
      <section className="hero" style={{ paddingTop: "120px", paddingBottom: "80px" }}>
        <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 24px" }}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.6 }}
          >
            <p
              style={{
                fontSize: "13px",
                fontWeight: 600,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "rgba(59, 130, 246, 0.8)",
                marginBottom: "16px",
              }}
            >
              CONTACT
            </p>
            <h1
              style={{
                fontSize: "clamp(36px, 5vw, 56px)",
                fontWeight: 600,
                lineHeight: 1.1,
                marginBottom: "20px",
                color: "#1e293b",
              }}
            >
              Talk to the team.
            </h1>
            <p
              style={{
                fontSize: "18px",
                lineHeight: 1.6,
                color: "rgba(30, 41, 59, 0.7)",
                maxWidth: "720px",
              }}
            >
              We reply with clarity. No scripts.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Contact Options Grid */}
      <section style={{ padding: "80px 24px", maxWidth: "1100px", margin: "0 auto" }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "24px",
              marginBottom: "80px",
            }}
          >
            {/* Email Card */}
            <div
              style={{
                padding: "32px",
                background: "rgba(255, 255, 255, 0.6)",
                backdropFilter: "blur(20px)",
                border: "1px solid rgba(255, 255, 255, 0.4)",
                borderRadius: "16px",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.06)",
              }}
            >
              <h3
                style={{
                  fontSize: "18px",
                  fontWeight: 600,
                  marginBottom: "12px",
                  color: "#1e293b",
                }}
              >
                Email
              </h3>
              <p
                style={{
                  fontSize: "15px",
                  lineHeight: 1.6,
                  color: "rgba(30, 41, 59, 0.8)",
                  marginBottom: "12px",
                  fontFamily: "monospace",
                }}
              >
                hello@cognitivesystem.ai
              </p>
              <p
                style={{
                  fontSize: "13px",
                  color: "rgba(30, 41, 59, 0.6)",
                  marginBottom: "16px",
                }}
              >
                Security disclosures welcome.
              </p>
              <button
                onClick={copyEmail}
                style={{
                  padding: "10px 20px",
                  background: copiedEmail ? "#10b981" : "#3b82f6",
                  color: "white",
                  borderRadius: "8px",
                  fontSize: "14px",
                  fontWeight: 600,
                  border: "none",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                {copiedEmail ? "Copied!" : "Copy email"}
              </button>
            </div>

            {/* Social Card */}
            <div
              style={{
                padding: "32px",
                background: "rgba(255, 255, 255, 0.6)",
                backdropFilter: "blur(20px)",
                border: "1px solid rgba(255, 255, 255, 0.4)",
                borderRadius: "16px",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.06)",
              }}
            >
              <h3
                style={{
                  fontSize: "18px",
                  fontWeight: 600,
                  marginBottom: "12px",
                  color: "#1e293b",
                }}
              >
                Updates
              </h3>
              <p
                style={{
                  fontSize: "15px",
                  lineHeight: 1.6,
                  color: "rgba(30, 41, 59, 0.7)",
                  marginBottom: "16px",
                }}
              >
                Follow product notes and releases.
              </p>
              <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                <a
                  href="#"
                  style={{
                    padding: "10px 20px",
                    background: "rgba(255, 255, 255, 0.8)",
                    color: "#3b82f6",
                    borderRadius: "8px",
                    fontSize: "14px",
                    fontWeight: 600,
                    textDecoration: "none",
                    border: "1px solid rgba(59, 130, 246, 0.3)",
                    transition: "all 0.2s ease",
                  }}
                >
                  X / Twitter
                </a>
                <a
                  href="#"
                  style={{
                    padding: "10px 20px",
                    background: "rgba(255, 255, 255, 0.8)",
                    color: "#3b82f6",
                    borderRadius: "8px",
                    fontSize: "14px",
                    fontWeight: 600,
                    textDecoration: "none",
                    border: "1px solid rgba(59, 130, 246, 0.3)",
                    transition: "all 0.2s ease",
                  }}
                >
                  LinkedIn
                </a>
              </div>
            </div>
          </div>

          {/* Contact Form */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.6 }}
            style={{
              padding: "48px",
              background: "rgba(255, 255, 255, 0.6)",
              backdropFilter: "blur(20px)",
              border: "1px solid rgba(255, 255, 255, 0.4)",
              borderRadius: "20px",
              boxShadow: "0 12px 32px rgba(0, 0, 0, 0.08)",
            }}
          >
            <h2
              style={{
                fontSize: "28px",
                fontWeight: 600,
                marginBottom: "32px",
                color: "#1e293b",
              }}
            >
              Send us a message
            </h2>
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: "24px" }}>
                <label
                  htmlFor="name"
                  style={{
                    display: "block",
                    fontSize: "14px",
                    fontWeight: 600,
                    marginBottom: "8px",
                    color: "#1e293b",
                  }}
                >
                  Name *
                </label>
                <input
                  id="name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  aria-invalid={!!errors.name}
                  aria-describedby={errors.name ? "name-error" : undefined}
                  style={{
                    width: "100%",
                    padding: "12px 16px",
                    fontSize: "15px",
                    border: errors.name ? "2px solid #ef4444" : "1px solid rgba(203, 213, 225, 0.5)",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.8)",
                    outline: "none",
                    transition: "all 0.2s ease",
                  }}
                  onFocus={(e) => {
                    if (!errors.name) e.currentTarget.style.border = "2px solid #3b82f6";
                  }}
                  onBlur={(e) => {
                    if (!errors.name) e.currentTarget.style.border = "1px solid rgba(203, 213, 225, 0.5)";
                  }}
                />
                {errors.name && (
                  <p
                    id="name-error"
                    style={{ fontSize: "13px", color: "#ef4444", marginTop: "6px" }}
                  >
                    {errors.name}
                  </p>
                )}
              </div>

              <div style={{ marginBottom: "24px" }}>
                <label
                  htmlFor="email"
                  style={{
                    display: "block",
                    fontSize: "14px",
                    fontWeight: 600,
                    marginBottom: "8px",
                    color: "#1e293b",
                  }}
                >
                  Email *
                </label>
                <input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  aria-invalid={!!errors.email}
                  aria-describedby={errors.email ? "email-error" : undefined}
                  style={{
                    width: "100%",
                    padding: "12px 16px",
                    fontSize: "15px",
                    border: errors.email ? "2px solid #ef4444" : "1px solid rgba(203, 213, 225, 0.5)",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.8)",
                    outline: "none",
                    transition: "all 0.2s ease",
                  }}
                  onFocus={(e) => {
                    if (!errors.email) e.currentTarget.style.border = "2px solid #3b82f6";
                  }}
                  onBlur={(e) => {
                    if (!errors.email) e.currentTarget.style.border = "1px solid rgba(203, 213, 225, 0.5)";
                  }}
                />
                {errors.email && (
                  <p
                    id="email-error"
                    style={{ fontSize: "13px", color: "#ef4444", marginTop: "6px" }}
                  >
                    {errors.email}
                  </p>
                )}
              </div>

              <div style={{ marginBottom: "24px" }}>
                <label
                  htmlFor="topic"
                  style={{
                    display: "block",
                    fontSize: "14px",
                    fontWeight: 600,
                    marginBottom: "8px",
                    color: "#1e293b",
                  }}
                >
                  Topic
                </label>
                <select
                  id="topic"
                  value={formData.topic}
                  onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "12px 16px",
                    fontSize: "15px",
                    border: "1px solid rgba(203, 213, 225, 0.5)",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.8)",
                    outline: "none",
                    cursor: "pointer",
                  }}
                >
                  <option value="General">General</option>
                  <option value="Security">Security</option>
                  <option value="Partnership">Partnership</option>
                  <option value="Support">Support</option>
                </select>
              </div>

              <div style={{ marginBottom: "24px" }}>
                <label
                  htmlFor="message"
                  style={{
                    display: "block",
                    fontSize: "14px",
                    fontWeight: 600,
                    marginBottom: "8px",
                    color: "#1e293b",
                  }}
                >
                  Message *
                </label>
                <textarea
                  id="message"
                  value={formData.message}
                  onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                  aria-invalid={!!errors.message}
                  aria-describedby={errors.message ? "message-error" : undefined}
                  rows={6}
                  style={{
                    width: "100%",
                    padding: "12px 16px",
                    fontSize: "15px",
                    border: errors.message ? "2px solid #ef4444" : "1px solid rgba(203, 213, 225, 0.5)",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.8)",
                    outline: "none",
                    resize: "vertical",
                    fontFamily: "inherit",
                    transition: "all 0.2s ease",
                  }}
                  onFocus={(e) => {
                    if (!errors.message) e.currentTarget.style.border = "2px solid #3b82f6";
                  }}
                  onBlur={(e) => {
                    if (!errors.message) e.currentTarget.style.border = "1px solid rgba(203, 213, 225, 0.5)";
                  }}
                />
                {errors.message && (
                  <p
                    id="message-error"
                    style={{ fontSize: "13px", color: "#ef4444", marginTop: "6px" }}
                  >
                    {errors.message}
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={isSubmitting || isSuccess}
                style={{
                  padding: "14px 32px",
                  background: isSuccess ? "#10b981" : "#3b82f6",
                  color: "white",
                  borderRadius: "12px",
                  fontSize: "15px",
                  fontWeight: 600,
                  border: "none",
                  cursor: isSubmitting || isSuccess ? "not-allowed" : "pointer",
                  opacity: isSubmitting ? 0.7 : 1,
                  boxShadow: "0 4px 12px rgba(59, 130, 246, 0.3)",
                  transition: "all 0.2s ease",
                }}
              >
                {isSuccess ? "Message queued — we'll reply soon." : isSubmitting ? "Sending..." : "Send message"}
              </button>
            </form>
          </motion.div>
        </motion.div>
      </section>

      {/* Security Note */}
      <section style={{ padding: "0 24px 120px", maxWidth: "1100px", margin: "0 auto" }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.6 }}
          style={{
            padding: "24px 32px",
            background: "rgba(239, 246, 255, 0.5)",
            border: "1px solid rgba(59, 130, 246, 0.2)",
            borderRadius: "12px",
            textAlign: "center",
          }}
        >
          <p style={{ fontSize: "14px", color: "rgba(30, 41, 59, 0.8)", margin: 0 }}>
            <strong>Security:</strong> For sensitive reports, include 'SECURITY' in the subject.
          </p>
        </motion.div>
      </section>
    </motion.div>
  );
}
