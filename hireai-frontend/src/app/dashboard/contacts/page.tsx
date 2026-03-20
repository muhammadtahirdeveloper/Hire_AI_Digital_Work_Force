"use client";

import { useState, useCallback, useEffect } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import toast from "react-hot-toast";
import {
  Search,
  Plus,
  Mail,
  Building2,
  Phone,
  Calendar,
  ChevronLeft,
  Tag,
  X,
  User,
  Pencil,
  Trash2,
} from "lucide-react";

interface Contact {
  id: string;
  email: string;
  name: string;
  company: string;
  phone: string;
  category: string;
  status: string;
  tags: string[];
  notes: string;
  first_contact_date: string | null;
  last_contact_date: string | null;
  total_emails: number;
  created_at: string | null;
}

interface EmailHistory {
  id: number;
  from: string;
  action: string;
  tool: string;
  outcome: string;
  metadata: Record<string, unknown>;
  timestamp: string | null;
}

const TAG_OPTIONS = ["Lead", "Client", "VIP", "Candidate", "Partner"];
const CATEGORY_OPTIONS = ["other", "lead", "client", "vip", "candidate", "partner", "vendor"];

const categoryColors: Record<string, string> = {
  lead: "bg-blue-500/20 text-blue-400",
  client: "bg-green-500/20 text-green-400",
  vip: "bg-purple-500/20 text-purple-400",
  candidate: "bg-orange-500/20 text-orange-400",
  partner: "bg-cyan-500/20 text-cyan-400",
  vendor: "bg-yellow-500/20 text-yellow-400",
  other: "bg-gray-500/20 text-gray-400",
};

function formatDate(iso: string | null): string {
  if (!iso) return "N/A";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function ContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [filterCat, setFilterCat] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Contact | null>(null);
  const [emailHistory, setEmailHistory] = useState<EmailHistory[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [editing, setEditing] = useState(false);

  // Form state
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formCompany, setFormCompany] = useState("");
  const [formPhone, setFormPhone] = useState("");
  const [formCategory, setFormCategory] = useState("other");
  const [formNotes, setFormNotes] = useState("");
  const [formTags, setFormTags] = useState<string[]>([]);

  const fetchContacts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), limit: "20" });
      if (search) params.set("search", search);
      if (filterCat) params.set("category", filterCat);
      const res = await api.get(`/api/contacts?${params}`);
      const d = res.data?.data ?? res.data;
      setContacts(d.contacts || []);
      setTotal(d.total || 0);
      setPages(d.pages || 1);
    } catch {
      toast.error("Failed to load contacts");
    } finally {
      setLoading(false);
    }
  }, [page, search, filterCat]);

  useEffect(() => { fetchContacts(); }, [fetchContacts]);

  const loadEmailHistory = async (contact: Contact) => {
    setSelected(contact);
    setEditing(false);
    try {
      const res = await api.get(`/api/contacts/${contact.id}/emails?limit=20`);
      const d = res.data?.data ?? res.data;
      setEmailHistory(d.emails || []);
    } catch {
      setEmailHistory([]);
    }
  };

  const handleCreate = async () => {
    if (!formEmail) { toast.error("Email is required"); return; }
    try {
      await api.post("/api/contacts", {
        email: formEmail, name: formName, company: formCompany,
        phone: formPhone, category: formCategory, tags: formTags, notes: formNotes,
      });
      toast.success("Contact created");
      setShowAdd(false);
      resetForm();
      fetchContacts();
    } catch { toast.error("Failed to create contact"); }
  };

  const handleUpdate = async () => {
    if (!selected) return;
    try {
      await api.patch(`/api/contacts/${selected.id}`, {
        name: formName, company: formCompany, phone: formPhone,
        category: formCategory, tags: formTags, notes: formNotes,
      });
      toast.success("Contact updated");
      setEditing(false);
      fetchContacts();
      // Refresh selected
      setSelected({ ...selected, name: formName, company: formCompany, phone: formPhone,
        category: formCategory, tags: formTags, notes: formNotes });
    } catch { toast.error("Failed to update contact"); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this contact?")) return;
    try {
      await api.delete(`/api/contacts/${id}`);
      toast.success("Contact deleted");
      if (selected?.id === id) setSelected(null);
      fetchContacts();
    } catch { toast.error("Failed to delete"); }
  };

  const resetForm = () => {
    setFormName(""); setFormEmail(""); setFormCompany("");
    setFormPhone(""); setFormCategory("other"); setFormNotes(""); setFormTags([]);
  };

  const startEdit = (c: Contact) => {
    setFormName(c.name); setFormCompany(c.company); setFormPhone(c.phone);
    setFormCategory(c.category); setFormNotes(c.notes); setFormTags(c.tags);
    setEditing(true);
  };

  const toggleTag = (tag: string) => {
    setFormTags((prev) => prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]);
  };

  // --- Detail View ---
  if (selected) {
    return (
      <div className="space-y-6">
        <button onClick={() => setSelected(null)} className="flex items-center gap-1 text-sm text-text-3 hover:text-text-1">
          <ChevronLeft className="h-4 w-4" /> Back to Contacts
        </button>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-navy/20">
                  <User className="h-6 w-6 text-navy" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-text">{selected.name || selected.email}</h2>
                  <p className="text-sm text-text-3">{selected.email}</p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => startEdit(selected)}>
                  <Pencil className="h-3 w-3 mr-1" /> Edit
                </Button>
                <Button size="sm" variant="outline" className="text-danger" onClick={() => handleDelete(selected.id)}>
                  <Trash2 className="h-3 w-3 mr-1" /> Delete
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardBody>
            {editing ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-text-3">Name</label>
                    <input value={formName} onChange={(e) => setFormName(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-border bg-bg-3 px-3 py-2 text-sm text-text" />
                  </div>
                  <div>
                    <label className="text-xs text-text-3">Company</label>
                    <input value={formCompany} onChange={(e) => setFormCompany(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-border bg-bg-3 px-3 py-2 text-sm text-text" />
                  </div>
                  <div>
                    <label className="text-xs text-text-3">Phone</label>
                    <input value={formPhone} onChange={(e) => setFormPhone(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-border bg-bg-3 px-3 py-2 text-sm text-text" />
                  </div>
                  <div>
                    <label className="text-xs text-text-3">Category</label>
                    <select value={formCategory} onChange={(e) => setFormCategory(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-border bg-bg-3 px-3 py-2 text-sm text-text">
                      {CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-xs text-text-3">Tags</label>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {TAG_OPTIONS.map((tag) => (
                      <button key={tag} onClick={() => toggleTag(tag)}
                        className={cn("rounded-full px-3 py-1 text-xs border",
                          formTags.includes(tag) ? "bg-navy text-white border-navy" : "border-border text-text-3")}>
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-text-3">Notes</label>
                  <textarea value={formNotes} onChange={(e) => setFormNotes(e.target.value)} rows={3}
                    className="mt-1 w-full rounded-lg border border-border bg-bg-3 px-3 py-2 text-sm text-text" />
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={handleUpdate}>Save</Button>
                  <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center gap-2 text-sm">
                  <Building2 className="h-4 w-4 text-text-3" />
                  <span className="text-text-3">Company:</span>
                  <span className="text-text">{selected.company || "N/A"}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="h-4 w-4 text-text-3" />
                  <span className="text-text-3">Phone:</span>
                  <span className="text-text">{selected.phone || "N/A"}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Calendar className="h-4 w-4 text-text-3" />
                  <span className="text-text-3">First contact:</span>
                  <span className="text-text">{formatDate(selected.first_contact_date)}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Mail className="h-4 w-4 text-text-3" />
                  <span className="text-text-3">Total emails:</span>
                  <span className="text-text">{selected.total_emails}</span>
                </div>
                <div className="col-span-2 flex items-center gap-2 text-sm">
                  <Tag className="h-4 w-4 text-text-3" />
                  <span className="text-text-3">Tags:</span>
                  {selected.tags.length > 0 ? selected.tags.map((t) => (
                    <Badge key={t} variant="secondary">{t}</Badge>
                  )) : <span className="text-text-4">None</span>}
                </div>
                {selected.notes && (
                  <div className="col-span-2 text-sm">
                    <p className="text-text-3 mb-1">Notes:</p>
                    <p className="text-text whitespace-pre-wrap">{selected.notes}</p>
                  </div>
                )}
              </div>
            )}
          </CardBody>
        </Card>

        {/* Email History */}
        <Card>
          <CardHeader>
            <h3 className="text-base font-semibold text-text">Email History</h3>
          </CardHeader>
          <CardBody>
            {emailHistory.length === 0 ? (
              <p className="text-sm text-text-4 text-center py-4">No email history found</p>
            ) : (
              <div className="space-y-2">
                {emailHistory.map((e) => (
                  <div key={e.id} className="flex items-center justify-between p-3 rounded-lg bg-bg-3">
                    <div>
                      <p className="text-sm text-text">{e.action}</p>
                      <p className="text-xs text-text-3">{e.timestamp ? formatDate(e.timestamp) : "N/A"}</p>
                    </div>
                    <Badge variant={e.outcome === "success" ? "default" : "destructive"}>{e.outcome}</Badge>
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    );
  }

  // --- Add Contact Modal ---
  if (showAdd) {
    return (
      <div className="space-y-6">
        <button onClick={() => { setShowAdd(false); resetForm(); }} className="flex items-center gap-1 text-sm text-text-3 hover:text-text-1">
          <ChevronLeft className="h-4 w-4" /> Back
        </button>
        <Card>
          <CardHeader><h2 className="text-lg font-semibold text-text">Add Contact</h2></CardHeader>
          <CardBody>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-text-3">Email *</label>
                  <input value={formEmail} onChange={(e) => setFormEmail(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-bg-3 px-3 py-2 text-sm text-text" placeholder="email@example.com" />
                </div>
                <div>
                  <label className="text-xs text-text-3">Name</label>
                  <input value={formName} onChange={(e) => setFormName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-bg-3 px-3 py-2 text-sm text-text" />
                </div>
                <div>
                  <label className="text-xs text-text-3">Company</label>
                  <input value={formCompany} onChange={(e) => setFormCompany(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-bg-3 px-3 py-2 text-sm text-text" />
                </div>
                <div>
                  <label className="text-xs text-text-3">Phone</label>
                  <input value={formPhone} onChange={(e) => setFormPhone(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-bg-3 px-3 py-2 text-sm text-text" />
                </div>
                <div>
                  <label className="text-xs text-text-3">Category</label>
                  <select value={formCategory} onChange={(e) => setFormCategory(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-bg-3 px-3 py-2 text-sm text-text">
                    {CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs text-text-3">Tags</label>
                <div className="mt-1 flex flex-wrap gap-2">
                  {TAG_OPTIONS.map((tag) => (
                    <button key={tag} onClick={() => toggleTag(tag)}
                      className={cn("rounded-full px-3 py-1 text-xs border",
                        formTags.includes(tag) ? "bg-navy text-white border-navy" : "border-border text-text-3")}>
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs text-text-3">Notes</label>
                <textarea value={formNotes} onChange={(e) => setFormNotes(e.target.value)} rows={3}
                  className="mt-1 w-full rounded-lg border border-border bg-bg-3 px-3 py-2 text-sm text-text" />
              </div>
              <Button onClick={handleCreate}>Create Contact</Button>
            </div>
          </CardBody>
        </Card>
      </div>
    );
  }

  // --- Contact List ---
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text">Contacts</h1>
        <Button size="sm" onClick={() => setShowAdd(true)}>
          <Plus className="h-4 w-4 mr-1" /> Add Contact
        </Button>
      </div>

      {/* Search + Filter */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-3" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search by name, email, or company..."
            className="w-full rounded-lg border border-border bg-bg-2 pl-10 pr-3 py-2 text-sm text-text placeholder:text-text-4"
          />
        </div>
        <select
          value={filterCat}
          onChange={(e) => { setFilterCat(e.target.value); setPage(1); }}
          className="rounded-lg border border-border bg-bg-2 px-3 py-2 text-sm text-text"
        >
          <option value="">All Categories</option>
          {CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* Results count */}
      <p className="text-xs text-text-3">{total} contact{total !== 1 ? "s" : ""} found</p>

      {/* Contact Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-36 rounded-xl bg-bg-2 animate-pulse" />
          ))}
        </div>
      ) : contacts.length === 0 ? (
        <div className="text-center py-12 text-text-3">
          <User className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p>No contacts found</p>
          <p className="text-xs mt-1">Contacts are auto-created when emails are processed</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {contacts.map((c) => (
            <div
              key={c.id}
              onClick={() => loadEmailHistory(c)}
              className="cursor-pointer rounded-xl border border-border bg-bg-2 p-4 hover:border-navy/40 transition-colors"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-text truncate">
                    {c.name || c.email}
                  </h3>
                  <p className="text-xs text-text-3 truncate">{c.email}</p>
                </div>
                <span className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full", categoryColors[c.category] || categoryColors.other)}>
                  {c.category}
                </span>
              </div>
              {c.company && (
                <p className="text-xs text-text-3 flex items-center gap-1 mb-1">
                  <Building2 className="h-3 w-3" /> {c.company}
                </p>
              )}
              <div className="flex items-center justify-between mt-3 text-xs text-text-4">
                <span>{c.total_emails} email{c.total_emails !== 1 ? "s" : ""}</span>
                <span>Last: {formatDate(c.last_contact_date)}</span>
              </div>
              {c.tags.length > 0 && (
                <div className="flex gap-1 mt-2">
                  {c.tags.slice(0, 3).map((t) => (
                    <span key={t} className="text-[10px] bg-bg-3 text-text-3 px-1.5 py-0.5 rounded">{t}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex justify-center gap-2">
          <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </Button>
          <span className="flex items-center text-sm text-text-3">
            Page {page} of {pages}
          </span>
          <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
