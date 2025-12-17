# GUI Visual Guide & Walkthrough

## Main Menu Overview

```
┌─────────────────────────────────────────────────────┐
│   🎬 YouTube Shorts Automation Suite                │
│   Schedule, manage, and automate your YouTube Shorts│
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ ▶ Run Automation (Schedule Videos)          │  │
│  ├─────────────────────────────────────────────┤  │
│  │ ➕ Add New Account                          │  │
│  ├─────────────────────────────────────────────┤  │
│  │ ⚙️  Manage Accounts                        │  │
│  ├─────────────────────────────────────────────┤  │
│  │ ❌ Exit                                      │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
│  📋 Features:                                       │
│  • Fetch unscheduled private videos                │
│  • Generate AI-powered metadata                    │
│  • Schedule videos with custom time slots          │
│  • Duplicate content detection                     │
│  • Multi-account support                           │
└─────────────────────────────────────────────────────┘
```

---

## Run Automation - Step 1: Review Videos

```
┌────────────────────────────────────────────────────┐
│ Step 1: Review Videos  Step 2: Settings  Step 3... │
├────────────────────────────────────────────────────┤
│                                                    │
│ Fetching your unscheduled private videos...       │
│ [████████████████░░░░░░░░░░░░░░░░░░░░░░░░]       │
│                                                    │
│ Unscheduled Private Videos                         │
│ ┌──────────────────────────────────────────────┐ │
│ │ Found 5 unscheduled private videos:          │ │
│ │                                              │ │
│ │ • video_id_1_abc123                          │ │
│ │ • video_id_2_def456                          │ │
│ │ • video_id_3_ghi789                          │ │
│ │ • video_id_4_jkl012                          │ │
│ │ • video_id_5_mno345                          │ │
│ │                                              │ │
│ └──────────────────────────────────────────────┘ │
│                                                    │
│ ✓ Ready to schedule 5 videos. Proceed to Step 2. │
└────────────────────────────────────────────────────┘
```

---

## Run Automation - Step 2: Schedule Settings

```
┌────────────────────────────────────────────────────┐
│ Step 1: Review Videos  Step 2: Settings  Step 3... │
├────────────────────────────────────────────────────┤
│                                                    │
│ Start Date                                         │
│ ┌──────────────────────────────────────────────┐ │
│ │ Select date (DD-MM-YYYY):                    │ │
│ │ [15-11-2025             ]                   │ │
│ └──────────────────────────────────────────────┘ │
│                                                    │
│ Videos Per Day                                     │
│ ┌──────────────────────────────────────────────┐ │
│ │ How many videos per day?                     │ │
│ │ [2]  ▼▲                                      │ │
│ └──────────────────────────────────────────────┘ │
│                                                    │
│ Daily Time Slots                                   │
│ ┌──────────────────────────────────────────────┐ │
│ │ Set time for each video:                     │ │
│ │ Time for video 1: [09:00]    (HH:MM format) │ │
│ │ Time for video 2: [15:00]    (HH:MM format) │ │
│ └──────────────────────────────────────────────┘ │
│                                                    │
│                          [Proceed to Processing] │
└────────────────────────────────────────────────────┘
```

---

## Run Automation - Step 3: Processing

```
┌────────────────────────────────────────────────────┐
│ Step 1: Review Videos  Step 2: Settings  Step 3... │
├────────────────────────────────────────────────────┤
│ Processing video 3/5                               │
│ [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 60%   │
│                                                    │
│ Processing Output                                  │
│ ┌──────────────────────────────────────────────┐ │
│ │ Starting automation...                       │ │
│ │                                              │ │
│ │ [1/5] Processing video_id_1_abc123...       │ │
│ │   ⏰ Scheduled for: 2025-11-15 09:00:00     │ │
│ │   📝 Fetching transcript...                 │ │
│ │   🤖 Generating metadata with Gemini...     │ │
│ │   📌 Title: 5 Viral Shorts Tips You Need...│ │
│ │   📤 Scheduling video...                    │ │
│ │   ✓ Video scheduled successfully!           │ │
│ │                                              │ │
│ │ [2/5] Processing video_id_2_def456...       │ │
│ │   ⏰ Scheduled for: 2025-11-15 15:00:00     │ │
│ │   ...                                        │ │
│ └──────────────────────────────────────────────┘ │
│                                                    │
│ [Start Processing]  [Close]                       │
└────────────────────────────────────────────────────┘
```

---

## Add New Account Dialog

```
┌────────────────────────────────────────────────────┐
│ Add New Account                                    │
├────────────────────────────────────────────────────┤
│                                                    │
│ Enter Account Name                                 │
│                                                    │
│ [personal________________]                         │
│                                                    │
│ Account name must contain only:                    │
│ • Letters (a-z, A-Z)                              │
│ • Numbers (0-9)                                    │
│ • Hyphens (-) and underscores (_)                  │
│                                                    │
│ Example: personal, business, channel_1             │
│                                                    │
│ Opening browser for authentication...              │
│                                                    │
│ ┌──────────────┐  ┌──────────────┐                │
│ │ Add Account  │  │   Cancel     │                │
│ └──────────────┘  └──────────────┘                │
└────────────────────────────────────────────────────┘

   ↓ Browser Opens ↓

┌────────────────────────────────────────────────────┐
│ Google Sign In                                     │
├────────────────────────────────────────────────────┤
│ Sign in with your YouTube account                  │
│ [ YouTube Account Login ]                          │
│                                                    │
│ Then click "Allow" for permissions...              │
└────────────────────────────────────────────────────┘

   ↓ Returns to GUI ↓

Success!
✓ Account added successfully!
  Account: personal
  Channel: My YouTube Channel
  ID: UCxxxxxxxxxxxxxx
```

---

## Manage Accounts - View Accounts

```
┌────────────────────────────────────────────────────┐
│ View  Account Operations  Data Management           │
├────────────────────────────────────────────────────┤
│                                                    │
│ Available Accounts                                 │
│                                                    │
│ Found 2 account(s):                                │
│ ┌──────────────────────────────────────────────┐ │
│ │ ✓ personal                                   │ │
│ │   Channel: My Personal Channel                │ │
│ │   ID: UCxxx1111111111111111111111111111     │ │
│ │                                              │ │
│ │ ✓ business                                   │ │
│ │   Channel: My Business Channel                │ │
│ │   ID: UCxxx2222222222222222222222222222     │ │
│ │                                              │ │
│ └──────────────────────────────────────────────┘ │
│                                                    │
│ [ Refresh ]                                        │
└────────────────────────────────────────────────────┘
```

---

## Manage Accounts - Account Operations

```
┌────────────────────────────────────────────────────┐
│ View  Account Operations  Data Management           │
├────────────────────────────────────────────────────┤
│                                                    │
│ Select Account                                     │
│ ┌──────────────────────────────────────────────┐ │
│ │ [personal           ▼]                       │ │
│ └──────────────────────────────────────────────┘ │
│                                                    │
│ Operations                                         │
│ ┌──────────────────────────────────────────────┐ │
│ │ [Refresh Credentials                      ] │ │
│ │ [Delete Account                           ] │ │
│ └──────────────────────────────────────────────┘ │
│                                                    │
│ After "Delete Account":                            │
│ Confirm Delete                                     │
│ Delete account 'personal'?                         │
│ This cannot be undone.                             │
│ [ Yes ]  [ No ]                                    │
└────────────────────────────────────────────────────┘
```

---

## Manage Accounts - Data Management

```
┌────────────────────────────────────────────────────┐
│ View  Account Operations  Data Management           │
├────────────────────────────────────────────────────┤
│                                                    │
│ Select Account                                     │
│ [personal           ▼]                             │
│                                                    │
│ Processed Videos Data                              │
│ ┌──────────────────────────────────────────────┐ │
│ │ Account: personal                            │ │
│ │ Channel ID: UCxxx1111111111111111111111      │ │
│ │                                              │ │
│ │ Total Processed Videos: 12                   │ │
│ │                                              │ │
│ │ Successfully Scheduled: 11                   │ │
│ │ Duplicates Detected: 1                       │ │
│ │ Processing Errors: 0                         │ │
│ │                                              │ │
│ │ Last Updated: 2025-11-14T15:30:45           │ │
│ │                                              │ │
│ │ Recent Videos:                               │ │
│ │ • vid_abc123                                 │ │
│ │   Title: 5 Secret Hacks...                  │ │
│ │   Status: scheduled                          │ │
│ │ ...                                          │ │
│ └──────────────────────────────────────────────┘ │
│                                                    │
│ [ View Summary ]  [ Cleanup Old Data ]             │
└────────────────────────────────────────────────────┘
```

---

## Status Icons Legend

| Icon | Meaning |
|------|---------|
| ✓ | Success / Valid |
| ✗ | Failed / Error |
| ⏰ | Scheduling / Time |
| 📝 | Transcript / Text |
| 🤖 | AI / Gemini |
| 📌 | Title / Metadata |
| 📤 | Upload / Schedule |
| ⚠️ | Warning |
| ℹ️ | Information |
| 🔐 | Authentication |
| 🎬 | Video |
| 📊 | Statistics |
| 💾 | Data / Storage |
| ❌ | Exit / Cancel |
| ➕ | Add |
| ⚙️ | Settings / Manage |

---

## Workflow Flowchart

```
START
  ↓
┌─────────────────────┐
│  Main Menu          │
│  1. Run Automation  │
│  2. Add Account     │
│  3. Manage Accounts │
│  4. Exit            │
└─────────────────────┘
  ↓ ↓ ↓ ↓
  │ │ │ └→ EXIT
  │ │ │
  │ │ └→ MANAGE ACCOUNTS
  │ │      ├→ View
  │ │      ├→ Operations (Refresh/Delete)
  │ │      └→ Data (Stats/Cleanup)
  │ │
  │ └→ ADD ACCOUNT
  │      ├→ Enter Name
  │      ├→ OAuth Login
  │      └→ Success/Error
  │
  └→ RUN AUTOMATION
       ├→ Step 1: Review Videos
       │  └→ Fetch from YouTube
       ├→ Step 2: Configure
       │  ├→ Set Start Date
       │  ├→ Videos Per Day
       │  └→ Time Slots
       └→ Step 3: Process
          ├→ Get Transcript
          ├→ Check Duplicates
          ├→ Generate Metadata
          ├→ Schedule Video
          └→ Save Data
```

---

## Color Indicators

```
✓ Green/Blue   = Success, Active, Ready
✗ Red          = Error, Failed, Stop
⚠️ Orange       = Warning, Needs Attention
ℹ️ Gray         = Information, Inactive
```

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Submit Form | Enter/Return |
| Cancel | Esc |
| Tab to Next | Tab |
| Tab to Previous | Shift+Tab |
| Copy | Ctrl/Cmd+C |
| Paste | Ctrl/Cmd+V |

---

## Performance Indicators

- ⏳ **Waiting**: Processing in background
- ⚡ **Fast**: < 2 seconds
- ⏱️ **Normal**: 2-10 seconds
- 🐢 **Slow**: > 10 seconds

---

## Notes for Users

1. **Don't close window** during "Step 3: Processing"
2. **Internet required** for YouTube API calls
3. **Timestamps** are in your local timezone
4. **Duplicates** are automatically skipped
5. **All data** is saved locally for recovery

---

**First time? Start with GUI_QUICKSTART.md**
