# The Tank: Installer (Instructions for the AI)

The user gave you this file to install The Tank. Read this file from start to end before you do a step. Then do the steps in sequence.

The Tank is only markdown files. It contains no software to run. It works with each AI that can read files or receive pasted text.

## Step 1: Tell the user what you will do

1. Tell the user that you will install The Tank, test it, and show how to start. Use three sentences or fewer.
2. Continue to Step 2. Do not wait for an answer.

## Step 2: Identify your platform type

Select the first type that is true for you.

| Type | Your platform | Examples |
|---|---|---|
| A | You can read and write files in a folder on the computer of the user | Claude Code, Codex, Cursor, Gemini CLI, Hermes, other file-system agents |
| B | You are a chat assistant with a project or knowledge feature that keeps uploaded files and instructions | ChatGPT Projects or custom GPTs, Claude Projects, Gemini Gems |
| C | You are a chat assistant that cannot keep files | Any chat with no project feature |

Tell the user the type that you selected. Then go to the step for that type.

## Step 3A: Install on a file-system agent

1. Find the folder that contains this file. This folder is the package folder.
2. Ask the user where to install The Tank. Suggest a new folder named `the-tank` in the home folder of the user.
3. Copy the `system` folder and the `workspace` folder from the package folder to the install folder.
4. Copy `OPERATIONS-MANUAL.md` and `README.md` to the install folder.
5. Make the start file for your platform in the install folder:

   | Platform | Start file name |
   |---|---|
   | Claude Code | `CLAUDE.md` |
   | Codex, and each tool that reads `AGENTS.md` | `AGENTS.md` |
   | Gemini CLI | `GEMINI.md` |
   | Each other platform | `AGENTS.md`, and tell the user to set it as the system prompt or rules file |

6. Write this text in the start file:

   ```
   This folder contains The Tank. At the start of each session, read system/START-HERE.md and obey it.
   ```

7. If a start file with that name is already in the folder, do not replace it. Add the text at the end of the file.
8. Go to Step 4.

## Step 3B: Install on a chat assistant with projects

You cannot do these steps yourself. Give the user these steps, one at a time, and wait for the user to do each step.

1. Tell the user to make a new project (or custom GPT, or Gem) with the name "The Tank".
2. Tell the user to upload 7 files from the `upload-pack` folder: `TANK-CORE.md` and the six `PRECEDENTS-<NAME>.md` files.
3. Tell the user not to upload `PROJECT-INSTRUCTIONS.md`.
4. Tell the user to open `upload-pack/PROJECT-INSTRUCTIONS.md` and copy all of its text.
5. Tell the user to paste the text into the instructions field of the project.
6. Tell the user to open a new chat in the project and give this installer again.
7. In that new chat, go to Step 4.

## Step 3C: Install on a chat assistant with no files

1. Tell the user that this type works with less accuracy, because the past-pitch library is too large to paste.
2. Tell the user to paste the full text of `upload-pack/TANK-CORE.md` at the start of each chat.
3. In this mode, skip the "Find past pitches" part of the judge procedure. Write "No past pitches available" in the evidence.
4. Go to Step 4.

## Step 4: Do the self-test

1. Read `system/START-HERE.md` (in Type B or C, read the start of `TANK-CORE.md`).
2. Do `procedures/run-a-pitch.md` with the Cuban Shark only. Use the pitch in `system/tests/sample-pitch.md`. Do not ask intake questions. The sample pitch is complete.
3. Do the checks in `system/tests/self-test-checks.md`.
4. Tell the user the result: PASS, or FAIL and the check that failed.
5. If the result is FAIL, do the install step again one time. Then do the self-test again.

## Step 5: Tell the user how to start

1. Tell the user that The Tank is installed.
2. Tell the user to say "New pitch" and describe the business.
3. Tell the user that `OPERATIONS-MANUAL.md` has the full instructions.
4. Show this notice: "These are simulated investor models built from public records. They are not the real people and do not speak for them."
