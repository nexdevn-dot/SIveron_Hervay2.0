# Siveron – Help and workflows

This edition is generated from the same source as the in-app manual.

## Create optimization reports from signals

Create an evidence-linked report for each selected company from saved signals. Opportunities, other observations and open checks remain separate.

**Workflow:** Select companies → Actions → Optimization report → Choose categories and language → Review evidence → Export

1. **Selection and options** Select 1–20 companies and choose Actions → Create optimization report. For one company, use its own Actions menu; the bulk selection stays unchanged. Choose signal categories, German or English and maximum evidence age of 1–365 days. Create reports for selection saves a separate snapshot per company. No new websites are fetched and no signals are activated.

2. **Interpret results** Opportunities are conditional advice for sufficiently recent, active, evidenced signals. Review order is not a revenue or urgency score. Other observations are context. Missing, stale, inactive or low-confidence data remains open checks. Missing source links also prevent supported recommendations. The bar shows counts, not a company score.

3. **Review sources and limits** Review value, source link, observation date and collection confidence. A missing website in a listing does not prove no website exists. Booking is not suitable for every company; crawler restrictions may be intentional. The report is not a complete company audit and promises no savings or revenue growth.

4. **Optionally add AI** Add AI explanation uses the existing AI connection and processes usable evidence from this report. Unknown findings are omitted. The explanation is separately labelled and requires review. If AI is unavailable the factual report remains available. The extended analysis explains digital visibility, AI search, possible customer acquisition, next steps and limits for up to six evidenced signals. General reference sources remain separate from company evidence. Extend AI analysis explicitly upgrades older explanations; failures retain the previous text. An already extended analysis is reused.

5. **Export and history** Select the company and one of its latest 20 saved reports. Download Markdown exports a file. PDF / Print opens the print view; choose Save as PDF in your browser. Saved reports do not change when new signals arrive. Create a new report to include them. Reports for removed companies become accessible after restoration.

**Outcome and considerations:** A report neither prepares a campaign nor sends a message. Review all recommendations and AI text before external sharing.

## Research a contact’s email

Research published email addresses using name, company, domain and location. Research changes the contact only after explicit adoption.

**Workflow:** Contact → Actions → Research email → Choose sources → Review finding and source → Adopt address

1. **Open research** Choose Actions → Research email for a contact. Select the company website, public web, public profile hints or optional Hunter. Choose Start research. Quick stops after an explicit personal match; Thorough checks further sources within the configured limits.

2. **Configure sources and usage** Settings → Contact research controls sources, provider, default mode, page and query limits. Web search and targeted LinkedIn, Facebook or TikTok searches require a SerpApi or Serper key. Hunter is off by default and requires its own key. External searches send search criteria to the provider. Local monthly request limits use UTC months; 0 pauses the respective API. Reserved failed requests also count. SerpApi additionally retains the shared free-tier limit.

3. **Interpret findings** Each finding shows its source and discovery date. Explicit person association means the published person entity links name and email in the company context. Company mailbox and Unclear association are not confirmed personal addresses. Hunter findings remain provider suggestions. Public profile hints assist manual review; restricted or unreadable profiles may provide only a link.

4. **Adopt deliberately** Open the source, check the correct person and select one address. Acknowledge source review. Replacing an existing address requires additional confirmation; unclear personal association requires another acknowledgment. Blocks, duplicates and changed contacts prevent invalid adoption. Contact notes record the source. Address changes reset technical verification and cancel affected queued local messages.

5. **Review later or stop** Close the dialog while research continues. Reopening shows this contact’s latest research. Stop search ends after the in-flight operation. A process restart retains partial findings; paid requests do not resume automatically.

**Outcome and considerations:** This feature does not guess addresses or bypass logins or captchas. Missing results do not prove that no address exists. Research and adoption neither verify a mailbox nor send a message.

## Research and adopt B2B decision makers

Find potential decision makers on public company websites, review their published role and add selected people to Contacts.

**Workflow:** Choose companies → Choose target roles → Start research → Review source and fit → Add to Contacts

1. **Open research** Open Contacts → Research decision makers or Companies → Actions → Research decision makers. The latter prefills selected companies. Search for more known companies and select them individually. Research starts only when you choose Start research.

2. **Select target roles** Choose management/owner, sales, marketing, IT/engineering, HR, finance, purchasing or operations. Multiple roles are alternatives. Public company pages, such as Team and Contact, are researched. Without a website this source cannot find people. This version does not connect a licensed people-data provider.

3. **Review fit and source** Matching roles are derived from published titles. Role not established means unknown, not unsuitable. Former roles and support/training are shown separately. A title does not prove buying authority. Open the original source and check name, company, role and contact details. Review and edit opens the existing contact editor.

4. **Add selected people** Select the reviewed people and acknowledge source review. Add selected people to Contacts creates contacts or reports existing duplicates. People without a published email can also be stored. Errors or changed suggestions require individual review. Adoption does not verify email or start a campaign.

5. **Continue later** Close the window while a run continues; the run remains saved. Reopening shows the latest decision-maker research. Stop search ends it after in-flight companies. Use Next and Previous to browse results.

**Outcome and considerations:** The workflow is inspired by OpenOutFind and independently implemented. No email addresses are guessed and no login-protected profiles are scraped.

## Work with the AI assistant

Open Assistant at the bottom right. Ask for help, prepare search proposals and analyze saved companies or signals.

**Workflow:** Enter request → Review plan → View results → Start action yourself

1. **Customize the assistant** Under Settings → AI assistant, customize name, response language, response length, enabled features, conversation context and result count. Additional response preferences are optional. Saving changes neither sending approvals nor AI credentials.

2. **Describe a search** For example: Find construction companies within 25 km of Gütersloh. Review the proposal and choose Review in Discover. Edit criteria, check the source and preview, then start the search yourself. Results use the existing company data model.

3. **Analyze saved data** Ask about a known signal, signal category or companies in a location. The database calculates results. Match, no match and unknown remain separate. Missing, old or inactive evidence is unknown. Signal summaries count per signal; companies may appear in several rows. Next and Previous paginate without another AI call. Company names open the profile.

4. **Understand limits and history** Unsupported criteria, such as revenue thresholds, require clarification. The assistant does not send, delete or approve. Requests and configured conversation context are processed through the existing AI connection. History remains only in the open browser and is removed by Clear or reload. Use the regular features if AI is unavailable.

**Outcome and considerations:** Reports describe recorded evidence, not complete market coverage. This first version supports individual signals and simple company filters.

## Adopt a company contact with a chosen email

When a company has several known addresses, choose which email to use when creating a company contact.

1. **Open the address list** Open the company contact view in Companies and choose Adopt as company contact. Known company emails lists the currently stored addresses. Multiple addresses start without a selection. A single address prefills only an empty input.

2. **Save the desired address** Select an address from the list. It is copied to the Email field for review or editing. You may also enter a known address manually. Save the contact afterwards. Different addresses can become separate company contacts for the same organization; the same address is not duplicated.

**Outcome and considerations:** Selection copies no verification status and starts no sending. Existing named contacts are not automatically converted into company contacts.

## Email format and domain checks

Format, mail-transport support and domain evidence are different checks. None alone proves that a mailbox exists.

1. **Consistent format checks** Contacts and saved campaigns use the same server-side format checks. An unsupported format is marked in the contact view and is not ready for campaign selection. A technically unverified but supported address remains usable in the manual workflow; other sending rules still apply.

2. **Reuse DNS results** Public email lookup can check whether a domain can receive mail. Repeated checks reuse DNS answers until expiry. Timeouts remain unknown and are not treated as a missing mailbox. Simply opening contacts or campaigns performs no DNS check.

**Outcome and considerations:** No SMTP test connections or test messages are performed. These checks do not automatically change verification status, contact suppression or approvals.

## Review found company details

Public email and people searches can also detect explicitly published company details. They appear as suggestions in the company profile.

**Workflow:** Run lookup → Open profile → Check source → Adopt or dismiss

1. **Find suggestions** Open the company profile via its name. Review found details shows phone, address or contact-point email with source, reading time and organization or contact label. Only found details appear; missing structured data is not invented. Website profiling adds these suggestions only when CONTACT_FOUND is enabled.

2. **Compare existing values** Compare the suggestion with the current company value. Check especially that an address belongs to the right branch and the contact to the right organization. Website declarations do not confirm identity. Identical stored phone or location values are not offered again.

3. **Adopt or dismiss explicitly** Adopt detail changes only the displayed company field. Replacing an existing value requires confirmation. An adopted email remains technically unverified and creates no contact. Dismiss removes only the suggestion from pending review. If a value has changed meanwhile, close and reopen the profile.

**Outcome and considerations:** Page reads have time and size limits. A page can be reused within the same job. A failed read does not mean a company has no contact details. Adoption approves or sends no message and removes no suppression.

## Current quota readings

Usage separates your active provider’s quota from Siveron’s own calls.

1. **Check the reading time** Last checked shows when Siveron last read the provider’s limits. Automatic reads reuse a cache for up to five minutes. A quota reset time is a different timestamp.

2. **Refresh quota explicitly** Refresh quota now bypasses the cache. The button is disabled while reading. If the read fails, quota is shown as unavailable. No AI message is generated and no agent is started.

**Outcome and considerations:** The call and token totals below count Siveron only. Development work in Codex is not recorded there as a Siveron call.

## Delete selected companies

Select companies using their checkboxes and choose Actions → Delete selected companies. Without a selection, the action is disabled.

1. **Confirm your selection** The confirmation shows the number of selected companies, including selections across pages. Confirm only if these companies should leave your active list. Running email or people searches block deletion.

2. **Undo removal** After removal, Undo removal appears. It restores the last removal or cleanup batch. Undo remains available after reloading within the same browser session.

**Outcome and considerations:** Linked contacts, campaigns and sent messages are retained. Removing a company does not stop sending. Use contact suppression or sending pause for that purpose.

## Open a company profile

Click a company name in the cohort results under Signals or in Companies. Its profile opens above the current list.

1. **Review known details** The dialog shows stored domain, industry, location and size details, known emails, phone numbers, website and linked contacts. Missing details remain empty or display a dash. No new research starts.

2. **Return to the list** Use Close or Escape. Your list and filters remain intact. If the company has since been removed or cannot be loaded, close the dialog and refresh the list.

**Outcome and considerations:** Viewing does not change data, create contacts or send messages.

## Understand campaign progress

The connected steps show preparation. The delivery status below separately shows what is happening to messages.

**Workflow:** Contacts → Draft → Preview → Prepare → Approval

1. **Read and open steps** A check and Complete mark finished steps. A blue circle with Current step shows what to do next. Upcoming marks unfinished steps. Click a step to open its area. Small screens show steps vertically.

2. **Distinguish preparation and delivery** After approval is complete, no preparation step remains current. Below, sent messages, messages awaiting approval and approved messages are counted separately. Green means every counted message is recorded as sent. Yellow means delivery is pending; it does not confirm a running agent. Failures, rejections or cancellations require review.

**Outcome and considerations:** This display is not a time or percentage estimate and does not confirm receipt in the recipient’s inbox. Opening a step neither sends nor approves a message.

## Templates and sales opportunities

Reuse reviewed drafts and record the next sales step after an interested reply. Both workflows remain explicitly under your control.

**Workflow:** Save draft → Save template → Create empty draft → Review recipients and preview

1. **Save and reuse a template** Open a campaign and choose Save draft as template. Name it and optionally link a target profile or the current Discover criteria. Under Campaigns → Campaign templates, create a fresh draft without recipients. Messages and planning fields are copied; check personal details in the text. Sender, signature, attachments, recipients and approvals are excluded.

2. **Apply search criteria separately** Apply search criteria opens Discover with saved values. It starts no search. Review the source, locations, radius, preview and costs before starting. Automatic email lookup and resuming old search sections are disabled. Choose another target profile if the referenced one was deleted.

3. **Create an opportunity from a reply** Open an incoming reply in Conversations and choose Create or link opportunity. Confirm reviewed interest and enter a title, stage, next task and date. Owner and note are optional. Open stages require a task and date; Won and Lost may be saved without a next task.

4. **Maintain progress and retain sources** Under Conversations → Sales opportunities, filter and open entries. Update the stage, owner or next task as needed. Due open tasks appear in Today. A future date or closed stage removes the reminder. Additional conversations for the same contact can be linked while retaining their source campaigns.

**Outcome and considerations:** Saving sends no message or meeting invitation, approves nothing and does not remove contact suppression. An opportunity does not automatically assess conversation qualification or meeting outcomes. Task dates use UTC calendar days.

## How to work with Siveron

Siveron connects company research, contact management, message drafting and controlled sending. A company starts as a research record. A contact with an email address can become a recipient. A saved campaign is not a sent message.

**Workflow:** Discover → Companies → Contacts → Campaigns → Outbox → Conversations

1. **Find companies or enter known contacts** Start in Discover to find new companies. If you already know a person or company mailbox, start directly in Contacts → Add contact. Research is not a required step in that case.

2. **Prepare recipients and messages** Create company contacts from suitable companies or review suggested people. Select contacts with email addresses, create a campaign draft and check the text for each recipient in the preview.

3. **Proceed deliberately to sending** Prepare for review creates messages in the Outbox. Approving them there makes them eligible to send. The agent, mailbox, sending switch, daily limit and sending time must also allow delivery.

**Outcome and considerations:** The simplest starting point is a manual campaign with one known contact and one message. Neither company discovery nor an external verification service is required.

## Navigation and core concepts

The left sidebar stays visible on larger screens. On smaller screens, use Open navigation. Selecting a section closes the mobile menu; Escape also closes it. Scroll within the sidebar when its contents exceed the screen height.

| Section | What it is for |
| --- | --- |
| Today | Open decisions, pipeline counts, recent activity and discovery runs at a glance. |
| Signals | Review and confirm suggested prospecting signals; build cohorts from those signals. |
| Discover / Companies | Find new companies; filter existing companies, enrich contact details and research people. |
| Contacts / Campaigns | Manage and select recipients; draft message sequences and prepare them for review. |
| Outbox / Conversations | Review outgoing messages and track their status; read incoming conversations. |
| Activity / Usage | Inspect agent actions and check AI usage and available quotas. |
| Settings / Controls | Configure the mailbox, integrations and sending values; start or stop the background agent. |

**Outcome and considerations:** The auto, EN/DE and Refresh controls in the header change appearance, language or the current data view. Refresh does not start a search or the agent.

## Before sending for the first time

You can manage contacts and write manual drafts immediately. Actual sending requires a configured mailbox. The dashboard and background agent are separate: an open website does not mean the agent is running.

**Workflow:** Configure mailbox → Contact + draft → Review outbox → Check sending conditions

1. **Open Settings → mailbox** Use the existing Gmail/Google Workspace integration or SMTP + IMAP. SMTP requires your provider’s server, port, username and password or app password. IMAP is used to read replies. Campaign planning fields do not replace mailbox credentials.

2. **Authorize Gmail separately** Gmail requires a suitable OAuth client and a completed sign-in. Saving a client ID and secret alone does not connect the mailbox. Check the Gmail status shown in Settings. Complete the existing authorization step with scripts/harvey gmail auth in the project terminal.

3. **Set sending values deliberately** Under Settings → Email sending, enable the channel and set a daily limit greater than 0. Stop the agent before changing these values. Changes apply on the next start. Saving does not start the agent.

4. **Distinguish agent state from sending pause** Controls → Start Siveron starts background work. Pause sending in the Outbox pauses delivery. Before starting the agent or resuming sending, check already approved messages: they may then be sent.

**Outcome and considerations:** Manual campaigns use native SMTP/Gmail delivery. Instantly is an additional legacy integration, not a prerequisite for this workflow. Integrations may use external services and their quotas.

## Find companies

In Discover, choose the kinds of companies and the area to search. Supported business terms depend on the selected data source. Typing an unsupported category as free text does not add support for it.

**Workflow:** Choose source → Terms + locations → Check preview → Start search

1. **Select a suitable source** OpenStreetMap (Overpass) uses map data without an API key. Geoapify Places needs a configured key and has its own categories. SerpApi Web Search also needs a key and supports web-search terms. Google Maps (local) is an experimental browser search without a separate service or API key. It requires the locally installed Playwright Chromium browser.

2. **Confirm business terms** Select a suggestion or type your own term and confirm it with Enter. Selected terms appear as removable chips. An unconfirmed typed term can block starting the search. Check messages such as “Not supported by this source”.

3. **Set locations and radius** Choose location suggestions or enter a location manually when suggestions are unavailable. Multiple locations are supported. For map sources, the radius limits the search area. Without a location, configured target regions apply; this does not guarantee an exhaustive country-wide search.

4. **Read the preview before starting** Check generated queries, supported terms, area and available quotas. Additional search options include the result limit. Refresh preview checks the search plan; Start search actually collects companies.

**Outcome and considerations:** Example of a narrower search: construction companies + Frankfurt am Main + a suitable radius. Use multiple locations or another source to expand coverage. Results depend on the records published by each source.

## Search Google Maps locally

This source runs directly inside the Siveron backend. No additional server or browser extension is required. If Chromium is missing, the preview displays the installation command for the project terminal. The preview does not start a Google search.

**Workflow:** Location + radius → Review scope → Search locally → Import companies

1. **Choose coverage** Quick searches one map area per term and location. Thorough creates nine sections per combination. At most 100 sections and 200 listings per section are allowed. The preview displays the maximum before filtering and deduplication; this is not a promised result count.

2. **Understand filters and radius** All businesses is the default. Alternatively filter by a listed website, missing website or phone number. A missing listing website does not prove none exists. Listings outside the radius or without exact coordinates are not imported. Grid search does not guarantee complete coverage.

3. **Stop and resume** Stop is checked between browser actions; an ongoing navigation may first reach its timeout. Checkpoints are stored locally. With the same source, terms, locations, radius, result limit, filter and coverage, use Start search to resume with Resume saved search sections checked. Complete saved sections are reused rather than fetched again. Uncheck for fresh results. Nothing restarts automatically after a dashboard restart.

4. **Errors and next steps** Blocks or unreadable pages interrupt the run. No CAPTCHAs are solved and no accounts are signed in. Existing checkpoints are retained. Different Google listings sharing a website can remain separate branches. Existing values are not overwritten. The existing website profiling follows a successfully completed search; find public emails and people afterwards under Companies.

**Outcome and considerations:** Source terms apply. There are no API fees; local compute and network usage still apply. This feature is experimental and has not yet been proven reliable against the live site. Search results trigger neither outreach nor campaign approval.

## Understand search progress and result counts

During a search, Discover shows the current phase and its progress. Search details opens stages, elapsed time, email results and errors in a dialog. Closing it or pressing Escape leaves the search running; only Stop stops it. Completion shows a short summary. Hide summary collapses it under Last search. On reload the latest stored run is already collapsed. Percentages apply only to the current phase.

**Workflow:** Prepare locations → Search companies → Check websites → View results

| Display | Meaning and next action |
| --- | --- |
| Elapsed time / time remaining | Elapsed time is measured. A remaining-time estimate appears after enough entries complete and applies only to the current phase. It may disappear during unusually long waits. |
| New companies | New company records after matching and deduplication. This is not the number of raw records returned by the source. |
| Already known / observations | Known companies are not counted as new again. Multiple sources or queries may observe the same company. |
| Result limit reached | The source returned at least the requested raw-record limit. More results may exist. Raise the limit or change the area. This does not guarantee additional new companies. |
| Below the limit / not recorded | Below the limit means the measured queries did not reach the cap. Older runs or unmeasured sources cannot establish whether a cap was reached. Neither case proves complete market coverage. |

**Outcome and considerations:** Stop lets the current work item finish. Reloading shows stored progress. After a dashboard restart, interrupted company discovery may be marked interrupted and must be started again. There is no fixed maximum of 49 new companies.

## Manage companies and selection

Companies shows the collected company inventory with email, phone, website, industry, location and linked contacts. A company record by itself is not yet a campaign recipient.

1. **Narrow the list** Search by name and use location, industry, email or website filters. The list shows 30 companies per page. Reset filters returns to the unfiltered inventory.

2. **Select companies for a bulk action** Select individual rows or use Select this page. Selection persists across pages. Changing a filter clears it. The selected count is therefore more useful than the number of rows currently visible.

3. **Open the details you need** The company name opens its details. The contact count opens linked people. The email column initially shows one address; More email addresses and Check details reveal additional information.

4. **Distinguish research from contact creation** Find public emails for selection enriches company addresses. Find people for selection generates suggestions. Neither search automatically creates a campaign or approves messages.

**Outcome and considerations:** Closing a results dialog does not stop its search. Reopen it using View email search results or View suggested people; use Stop search to stop processing.

## Find public email addresses

The search reads addresses published on the official company website. It does not guess personal email patterns. A publicly listed address is neither proof of a working mailbox nor approval to send.

**Workflow:** Website known? → Read home and contact pages → Match addresses → Save address + source

1. **Start for one company or a selection** Use Find public email on a company or select several companies and start the bulk search above the list. Without a known website, the function cannot inspect that company’s site. First add the correct website in the relevant company form where available.

2. **Understand the extraction methods** Extraction covers visible text, mailto links, explicit forms such as [at] and structured email fields. It checks the home page and a limited set of contact/legal pages. A bounded browser-rendering fallback may be used. It cannot read every subpage or protected website.

3. **Review the result** Check the address, source and company association. An official contact block can establish an address on a different email domain. Third-party agency addresses are filtered where detected; reviewing the source remains useful.

4. **Interpret technical checks correctly** “Valid email format” checks syntax; “Mail domain present” is based on DNS. Neither confirms that a particular mailbox exists or accepts mail. New findings therefore remain unverified. A domain-check timeout does not remove an address that was found.

**Outcome and considerations:** For “no email”, inspect the site yourself: the address may be on an unread page, an image, behind a form or in an unusual format. You can enter a known address manually as a contact. “Unavailable / failed” indicates a reading or processing error, not necessarily an invalid company.

## Filter companies and save views

Filters check the entire active company inventory. The table then shows 30 matching records per page. Values within one field are alternatives (OR); different fields must all match (AND). Filtering performs no internet research.

**Workflow:** Locations + industries → Combine attributes → Review matches → Save view

1. **Search multiple selections** Type in Location or Industry to find stored values and select several entries. Berlin and Hamburg together with Hotel means: Hotel in Berlin OR Hamburg. Options are stored location/industry values, not a new geographical radius search. Remove individual values in the selection control or via filter chips.

2. **Combine additional attributes** Email and Website are directly visible. More filters opens Phone, named people, linked social profiles and Source. A company contact alone is not a named person. Phone and email also consider active associated contacts; deleted contacts are excluded. A linked profile does not verify identity.

3. **Read facet counts** The count next to a value respects every other active filter, but not the selection in its own field. This shows matches for an additional location or a different email status. Counts therefore need not equal the current table total. Zero-match values remain visible.

4. **Save and reuse views** Open Save current filters, enter a unique name of at most 60 characters and save. Up to 30 views are stored in the local Siveron database and survive reloads or restarts. They are shared within this local installation. Select a view to apply its filters. Row selection, page number and email lookup mode are not saved.

5. **Reset and remove** Every filter change clears row selection and returns to page 1. Reset filters clears all filters but retains saved views. Remove saved view deletes only the selected filter preset. Current filters and company data remain. Changes are locked during bulk email lookup.

**Outcome and considerations:** If saved values no longer occur in the inventory, a view can return zero matches. Remove individual chips or reset filters. Saved views do not change contacts, campaigns or send approvals.

## Extend and connect email search

Open the Actions menu under Companies to find email lookup, people lookup, cleanup and available search results with matching icons. A shared search mode controls single-company and bulk lookup under Companies. In Discover you can optionally enable public email search as a follow-up step. This automatic phase is off by default.

**Workflow:** Quick / Thorough → Read official pages → Review sources → Add contacts

1. **Choose search mode** Quick reads the homepage and, if needed, up to two contact/legal pages. Page lookup stops after a matching email. Thorough also considers about and team pages: at most six subpages after the homepage. Actual navigation links take priority over fallback paths, including German and English paths such as /kontakt, /contact-us and /about-us.

2. **Understand browser and time limits** Browser rendering is attempted only without a matching email: Quick at most one page, Thorough at most two. Overall processing per company is bounded to approximately 25 or 80 seconds. Stop waits for active individual lookups. Additional pages may yield more addresses but do not guarantee a result.

3. **Review noise filtering and profiles** Extraction filters technical error-tracking domains, asset filenames and hash-like strings. Numeric mailbox names and common free-email providers are not categorically discarded. Linked profiles under Phone / website show detected Facebook, Instagram, LinkedIn, TikTok and YouTube links with sources. Only links from the company website are stored; platforms are not automatically searched. Links do not verify a person’s identity.

4. **Connect with Discover** Enable Find public emails after company search and choose the mode before starting. After successful discovery and website profiling, a separate email phase checks only new or known companies returned by this run, at most 1000; excess entries are reported. Progress separates companies with email, no finding, no website and failures. A stopped or interrupted discovery run does not start this phase.

**Outcome and considerations:** Found addresses retain sources and technical evidence and remain unverified. Existing contacts and verified contact statuses are not overwritten. This extension creates neither people nor campaigns and sends no messages. A new Discover run can check the same companies again.

## Find and accept suggested people

People search is a research aid. It creates reviewable suggestions from public company pages. A name found on a website proves neither current employment nor responsibility for your offer.

**Workflow:** Select companies → Find people → Check source + role → Save contact

1. **Start the search** Select companies and click Find people for selection. The search reads the official site and a limited number of team, about, contact or legal pages. It is not a LinkedIn or general search-engine search.

2. **Review suggestions** Open the results dialog and check the name, company, role, source and discovery date. Progress counts companies; one company may yield zero, one or several suggested people. Suggestions are shown 20 per page.

3. **Accept or discard** Review and accept opens a prefilled form. Correct the data and select Save contact. Only then is a contact created. Discard hides an unsuitable suggestion. Email and phone are associated with a person only when explicitly published in that context.

4. **Add a missing email** A person can be saved without an email address but cannot yet be selected as an email recipient. Add a known address under Contacts → Edit, or use a general company contact. Names and email addresses are not invented.

**Outcome and considerations:** If you already know the person’s name, Add contact is faster than running another search. You can close the results dialog without stopping ongoing processing.

## Clean up unusable company records

Clean up records removes companies without usable contact information from the active inventory. It applies to the entire inventory, not just the selection, current filter or visible page.

**Workflow:** No valid email → No phone → No website / domain → Remove from active list

1. **Check the criteria** A company is cleaned up only when all criteria are true together: no known valid email, no phone and no website/domain. Known email addresses or phone numbers on linked people also protect the company record.

2. **Run cleanup** The button is next to the company bulk actions. Cleanup is disabled during a bulk email search. Filters and selection are reset after cleanup. The action does not perform new website or email-domain lookups.

3. **Undo if needed** Undo cleanup restores the last cleanup operation. History and linked contacts are not permanently deleted. Undo remains available in the same browser tab after reloading.

**Outcome and considerations:** The four boxes above describe an AND condition, not four separate deletion actions. A company with a website but no email is retained and can be researched further.

## Manually create a person or company contact

A contact is the record you assign to a campaign as a recipient. People and company contacts are distinct types, but both work in the manual campaign workflow. The original company is not deleted or turned into an invented person.

**Workflow:** Known person? → Create person with name → Otherwise use company mailbox → Select contact with email

1. **Enter a known person** Go to Contacts → Add contact and choose Person. First and last name are required. Add known email, role and phone. Link an existing company or create a company; a person without a linked company is also supported.

2. **Use a company as a recipient** Open a company’s details and select Create company contact. Review the prefilled general mailbox and save. A company contact does not require invented first or last names; use a general salutation in messages.

3. **Handle duplicates and conflicts** Repeated creation may reuse an existing contact. An email already linked to another contact can trigger a conflict. Check the existing record rather than creating the same address repeatedly.

4. **Select for a campaign** In Contacts, only unblocked records with a syntactically valid email can be selected. Select them and click Create campaign. An unverified technical status does not by itself block a manually prepared campaign.

**Outcome and considerations:** Adding a contact sends no email. People without an email remain useful for notes and later enrichment. Sending requires a recipient address.

## Edit contacts, notes, blocking and export

In Contacts, Actions opens a menu with matching icons: Notes, Edit, Do not contact and Delete. Contacts also provides search, a blocking filter, selection and 30 records per page. Selection persists across pages and clears when filters change. Editing a contact and blocking a contact have different consequences.

| Action | Effect and considerations |
| --- | --- |
| Edit | Corrects contact details and company association. Changing an email removes its earlier verification. Pending messages are cancelled when contact details are corrected so stale recipients or text are not reused. Prepare a new draft afterwards. |
| Notes | Shows history and stores new conversation or research notes. A note is not an email to the contact and does not imply automatic AI analysis. |
| Do not contact | Sets a block with a reason, excludes the contact from campaigns and cancels pending messages. A manual block can be explicitly lifted. A recipient opt-out cannot be lifted here. |
| Lift a block | Does not reactivate cancelled messages or paused campaigns. A previously opted-out address stays suppressed even if the contact’s email changes. |
| Actions → Delete | After confirmation, removes the contact from the active list and cancels pending messages. History and existing opt-outs are retained. Deleted contacts are excluded from campaign selection, company contact counts and CSV exports. The company itself is not deleted. |
| Deleted contacts → Actions → Restore | Shows deleted contacts and restores a selected contact after confirmation. Earlier blocks and opt-outs remain in effect. Cancelled messages and paused external campaigns are not reactivated. |
| Export verified contacts as CSV | Exports eligible records according to existing verification and blocking rules. “Export all” also includes other statuses and blocking fields; review these before using it as another sending list. Exporting sends nothing. |

**Outcome and considerations:** For external Instantly campaigns, blocking attempts to pause the entire affected campaign. If external confirmation is missing, check the warning and the provider directly. Already sent emails cannot be recalled.

## Save and evaluate target profiles

Under Signals, save required and excluded signals as a target profile. A profile neither activates signals nor removes companies.

**Workflow:** Select signals → Save profile → Check inventory → Read evidence

1. **Create a profile** Select required and excluded signals in the cohort builder. Enter a profile name and a maximum evidence age of 1–365 days below. Click Save target profile.

2. **Understand three outcomes** Match means all rules have sufficient recent evidence. No match means at least one rule is demonstrably unsatisfied. Unknown means evidence is missing, stale or insufficient, or the signal is inactive. An absent finding does not prove a characteristic is absent. Numeric rules check for a recorded value, not a threshold.

3. **Use evidence and search** Choose a saved profile and Check inventory. Evidence shows rule, value, source and date. The result filter includes unknown companies; counts cover the whole current inventory. Discover optionally accepts a profile and evaluates only that run after import and website checks. All companies are retained. Unrestricted search remains the default.

**Outcome and considerations:** A profile match does not approve sending. Contact selection, blocks and message approval remain separate.

## Understand email lookup failures and retry

Companies → Actions → View email search results shows lookup evidence for each company. A single public-email lookup also displays its diagnostic there.

1. **Check the cause** Open Lookup evidence for HTTP errors, timeouts, network problems, blocked external URLs or unavailable browser fallback, with source and attempt count. No finding describes only the checked pages. Older lookups without a recorded diagnostic are explicitly labeled.

2. **Retry within limits** For a completed bulk job, retry transient failures after at least 60 seconds. At most two retries per company in that job are allowed. Successful results are not repeated. Missing websites and permanent guard or format failures need correction. Stopped jobs are not resumed by retry. Lookup creates no contacts and sends nothing.

**Outcome and considerations:** Quick and thorough search limits still apply. A discovered address is not thereby confirmed deliverable.

## Complete tasks on Today

Today shows concrete tasks for replies, approvals and unknown or blocked delivery. Tasks derive from current state; multiple waiting messages in one campaign are grouped.

**Workflow:** Open task → Review record → Decide explicitly → List updates

1. **Review a reply** Open reply shows that conversation with its latest content. Record an outcome or explicitly mark the reply reviewed. That task then disappears. A new incoming reply appears again. Answered, closed and empty threads do not create reply tasks. Marking reviewed sends no reply and changes no contact block.

2. **Review approval or delivery** Review message opens an exact Outbox message. Only your separate approval there permits sending under the existing rules. This exact-message view offers no bulk approval. Inspect message shows delivery reasons and next steps. Ordinary waits alone do not create tasks. Sending, rejection, cancellation or resolved reasons update the list automatically.

3. **Changed tasks** Siveron rechecks each task before opening. Resolved tasks are removed. Loading failures show a warning; an empty list in that state is not proof that all work is done. Larger lists have pages and a complete total.

**Outcome and considerations:** The task list never starts the agent, approves email or automatically applies a proposed correction.

## Campaign results and manual assessment

Campaigns → Campaign results shows locally recorded stages, separating unique contact IDs from message counts. Stages are independent; they do not establish conversion rates or revenue impact.

1. **Understand period and counts** From and Through use UTC calendar days. Without dates, all dated local history is counted. One contact with two sent messages counts as one contact and two messages. Contactability is current email syntax without a known block, not proof of deliverability. Former contact IDs can remain in history.

2. **Recognize unknown data** Research cannot yet be reliably attributed to a campaign. External delivery and revenue are also unavailable. Undated legacy approvals, sends or replies are reported separately. Approval is not sending; provider acceptance does not prove inbox delivery. Linked records open the underlying contacts, messages and conversations.

3. **Record qualification or a meeting** Open a conversation. Under Record an outcome, choose Qualified, Not qualified or Not assessed and a meeting status. Add a note if useful and save. A positive reply does not fill these fields automatically. You can correct an assessment; editing only its note preserves the assessment date. Across multiple conversations for one contact in a campaign, the latest explicit assessment per field wins. No calendar invitation is sent.

**Outcome and considerations:** Saving an outcome approves no messages and changes neither contact status nor AI classification. Unassessed conversations are explicitly reported.

## Create a campaign from start to finish

A manual campaign combines selected contacts with up to ten messages. Start with contact selection, or create a draft directly in Campaigns and add contacts afterwards.

**Workflow:** Select contacts → Create draft → Review text + preview → Save draft → Prepare for review

1. **Your next step** The step guide connects contacts, draft, preview, preparation and approval. Click the next action or a step. Open Preview before preparation and check each message and recipient yourself. Reopen it after changes or reload. Opened does not automatically mean reviewed.

2. **Resume saved work** Save draft persists your work. Campaigns offers Resume last saved campaign. Only saved changes are restored; there is no autosave. After preparation, Review campaign in Outbox shows only this campaign. Show all campaigns clears the filter. Approval remains your separate decision.

3. **Assign contacts** Select recipients in Contacts and click Create campaign. Choose a new or existing manual draft. Alternatively, open Campaigns → Create campaign. Use Add recipients to search by name, company or email and select a contact. Chips show the selection; the cross removes a recipient. Open contact list provides the full inventory. Check the recipient summary for missing email addresses or blocks.

4. **Name and plan the campaign** Use a recognizable campaign name, for example “Initial outreach – region – month”. Planning fields hold audience, offer, goal, intended sender and a signature note. They are optional for manual writing; AI suggestions require offer and goal. They do not change the sending mailbox.

5. **Write and personalize messages** Fill in the subject and body for each step. Switch to Preview, select a recipient and check placeholders and salutation. The signature note is not appended automatically: include the desired signature in the actual message body.

6. **Save the draft** Saving persists an editable draft. Return through Campaigns → Open to continue. A full page reload can discard unsaved input. Save before leaving your work.

7. **Review previous outreach** If saved recipients belong to other campaigns, or the same email or linked company appears, the editor shows Review previous outreach. This also covers selected colleagues. Open Show matching records for campaign status, message status and previous send dates. A draft does not mean an email was sent. Equal company names without an established shared link are marked uncertain. Review the selection and remove unintended recipients or confirm the overlaps using the checkbox. You can then prepare for review. Changed evidence requires a fresh review. Blocks and opt-outs remain binding; follow-ups in the same sequence are not treated as a new campaign.

8. **Prepare for review** The button beside Save draft saves and validates recipients and rendered messages. Correct any reported issues. On success, individual messages appear in the Outbox and the campaign becomes read-only. Repeating preparation does not create extra copies.

**Outcome and considerations:** Contact status is another eligibility check: the manual flow accepts new, queued and suitable company contacts. Adding an email does not automatically make already contacted, blocked or opted-out recipients eligible again. Read the specific validation message.

## Sequence editor, placeholders and preview

Select a message on the left of the campaign editor; edit that step on the right. The editor stores supported formatting and a plain-text alternative. The toolbar provides bold, italic, underline, strikethrough, lists, quotes and links. Complex newsletter layouts and embedded images are not part of this editor.

1. **Manage messages** Add message inserts a step. Duplicate makes an independently editable copy. Dragging or Move up / Move down changes the order. Remove deletes a draft step; at least one message remains. Undo/redo applies to text editing.

2. **Set delays deliberately** The first step has no follow-up delay. Later steps accept 0–365 days. Each follow-up waits for the immediately preceding step to be sent successfully to the same contact in the same campaign, then for its stored delay. Late approval or an exhausted daily allowance does not shorten that delay. After success, the next queued time moves later if necessary; an already later date is preserved. Rejected or failed predecessors do not release follow-ups. Even a zero-day delay requires predecessor success first. Success means acceptance by the mail provider, not proof of inbox delivery.

3. **Insert placeholders** First name, Last name, Company, Title and Personalization buttons insert a placeholder into the last edited subject or body field. Supported placeholders are {{first_name}}, {{last_name}}, {{company}}, {{title}} and {{personalization}}. Missing data is not replaced with invented facts.

4. **Check different recipients** Preview shows the selected message using the selected contact’s data. Check at least one person and one company contact if both are present. A general salutation is preferable to a first-name placeholder for company mailboxes. Correct or remove unknown placeholders before preparing.

| Example – fictional contact data | Preview result |
| --- | --- |
| Hello {{first_name}} | With the example first name Alex: “Hello Alex”. If no first name exists, the personal part is missing; review the sentence manually. |
| {{company}} | Inserts the linked company if available. |

### What text limits apply before sending?

The sending check requires a nonempty subject and body. The subject may contain up to 90 characters, the body up to 220 words and at most one web link. Unresolved placeholders and certain unwanted promotional phrases are also blocked. A longer draft may be stored but must be shortened before preparation succeeds. Links behind labelled text also count towards the link limit.

**Outcome and considerations:** Longer sequences multiply the number of messages to review. Three contacts and two steps create up to six messages. Check follow-up timing before approval.

## Send formatting and file attachments

The toolbar formats selected text. Without a selection, formatting applies to text entered next. Link sets a web or mailto address; leaving the entry empty removes it. Insert emoji adds a symbol as text.

**Workflow:** Format text → Add files → Check preview + attachments → Prepare for review

1. **Choose attachments for each message** Add files opens the file picker. Supported formats are PDF, PNG, JPG, UTF-8 text/CSV, DOCX and XLSX. Each message can have up to five files, at most 10 MB each and 20 MB combined. Your mail provider may have lower limits; email encoding increases the total message size.

2. **Distinguish uploading from saving** After uploading, each file’s name and size appear below the message. Save the draft to retain this selection. Remove attachment detaches a file from the current message step. It does not remove uploaded files from stored history. Uploads are stored locally.

3. **Check every message step** Attachments belong to each message step and are carried over when duplicating. The copy can be edited independently. Remove unnecessary files from follow-ups. Preview displays formatting and file links for the selected recipient.

4. **Review the final message in the Outbox** After preparation, the Outbox shows personalized formatted text and attached filenames. Review both before approval. SMTP/Gmail receive the same file contents together with a plain-text alternative. Uploading or saving a draft sends nothing.

**Outcome and considerations:** This flow applies to native SMTP/Gmail sending. The legacy external Instantly flow does not support this extension. A real survey with response storage and analysis is still not part of this editor.

## What AI does when drafting

Suggest text with AI creates an editable suggestion from your planning fields. It is optional. You can write the entire campaign without AI. AI is not an automatic approval authority.

**Workflow:** Enter offer + goal → Request AI suggestion → Review / edit text → Save yourself

1. **Fill in offer and goal** Open Planning details for AI suggestions. Describe what you offer and the response you want. Audience and sender notes provide extra context. If offer or goal is missing, the button takes you to the missing field.

2. **Generate a suggestion** A waiting message appears during the request. The planning fields are sent to the configured AI integration, not the contact list. The current implementation requests one German email draft, even when the dashboard is in English. Changing the interface language does not translate message content.

3. **Protect existing text** If text already exists, you are asked before replacement. Confirming replaces the existing message sequence with the generated step. Copy any text you still need or deliberately save the earlier draft first.

4. **Review and continue yourself** Check facts, tone, offer, salutation and signature. The suggestion is not saved or sent automatically. Save it yourself, check the preview, then prepare it for review. If AI fails, continue writing manually.

**Outcome and considerations:** AI authentication, quotas and technical checks can prevent generation. Messages appear beside the AI button. Product training and knowledge files support additional automated agent workflows; they do not replace the planning fields required here.

## Outbox: review, approve and read status

Review individual prepared messages in the Outbox. Approval means that this particular message may be sent at its scheduled time. It is not confirmation that sending has succeeded.

**Workflow:** Awaiting approval → Approve → Queued → Sent or failed

1. **Read readiness and the next action** Ready means no known blockers were found at the last assessment; actual sending is not guaranteed. Waiting explains approval, a future time, a predecessor or the daily allowance. Blocked covers a pause, suppression, invalid content or missing mail setup. Unconfirmed means settings, legacy spacing or current runtime evidence could not be verified. Failed remains separate. More reasons reveals additional causes. Each reason has a next action; Open section only navigates and never sends. The assessment time appears above the list.

2. **Read the final message** Check recipient, subject, body, campaign and scheduled time. Placeholders should be resolved with actual data. Then Approve or Reject. Rejecting a message does not block the contact.

3. **Monitor the queue** Approved and scheduled contains approved messages that have not yet been sent. Nothing to review only means that no approval decision is outstanding. Messages below it may still be waiting for the agent, scheduled time or daily allowance.

4. **Read the traffic light and text together** Colours help scanning; the status text explains the exact situation. With no pending reviews, the view refreshes approximately every 15 seconds. Refresh also updates it manually.

- **Sent**: The mail service accepted the send successfully. This does not prove inbox placement or that the recipient read it.
- **Queued / Awaiting approval**: Yellow: not sent yet. Distinguish a pending human decision from an approved message awaiting execution.
- **Sending failed**: Red: the sending attempt failed. Read the error, check the mailbox and logs. An error state is not a successful send.
- **Rejected / Cancelled**: Grey: the message was not successfully sent and will not be processed normally in this state. A contact edit or block may cause cancellation.

**Outcome and considerations:** Pause sending is an additional control beyond approval. Existing approvals are retained; eligible messages may send after you resume.

## Why an approved email is still waiting

Work through this chain from top to bottom. The background agent must process the queue during a work cycle. Clicking Refresh alone does not trigger sending.

**Workflow:** Approved? → Agent running? → Sending enabled + unpaused? → Time + limit allow it? → Mailbox check succeeds?

| Check | Where to look and what to do |
| --- | --- |
| 1. Actually approved? | Outbox: “Awaiting approval” needs your decision. “Queued” is already approved. A saved campaign must first be prepared for review. |
| 2. Agent running and not blocked? | Check Controls and the header status. Starting deliberately enables background work. Read recent logs if the agent is paused, stopped or blocked by authentication or technical checks. |
| 3. Channel enabled and sending unpaused? | Check Settings → Email sending and the Outbox. Enable the channel, save values and start the agent with those values. The separate Outbox sending pause must also be lifted. |
| 4. Daily limit positive and not exhausted? | A daily limit of 0 prevents sending. Additional messages wait when the limit is exhausted. Changing it requires stopping the agent and applies on the next start; the change does not send immediately. |
| 5. Scheduled time due and outside quiet hours? | Check the scheduled time and configured timezone. Future dates and quiet hours hold messages. A scheduled time is not a guarantee of delivery at that exact minute. |
| 6. Mailbox and safety checks successful? | Missing or invalid credentials, unreadable replies, a contact block or an invalid address can stop delivery. Check logs in Controls and fix the cause first. |

**Outcome and considerations:** An exhausted AI budget pauses new AI text generation. Already approved native SMTP/Gmail messages can still be checked and sent if reply/bounce checks and all delivery rules succeed. Authentication or isolation failures can still stop the entire cycle.

## Track replies and conversations

Conversations shows stored threads, status and detected intent. The background agent reads replies using the configured mailbox connection; merely opening the dashboard does not run the full automated reply workflow.

**Workflow:** Reply received → Read mailbox → Stop pending follow-ups → Review conversation

1. **Read the thread** Check the sender, incoming message and previous outgoing text. This view displays history; it is not a free-form mailbox composer. Record personal context as a contact note.

2. **Distinguish replies from opt-outs** Detected replies stop pending native follow-ups. Clear opt-outs suppress the contact; bounces are handled separately. Do not bypass an opt-out by manually changing a status.

3. **Review AI replies** Full automated handling can classify replies and generate response drafts. With approval required, review outgoing text in the Outbox. A recorded conversation does not by itself mean that another reply has been sent.

**Outcome and considerations:** When AI usage is exhausted, replies may initially be processed only for sending safety. Full AI analysis can follow later. If an external sending tool is involved, also check its actual campaign status.

## Signals and automated workflows

Signals describe the traits of a suitable prospect. They support controlled automated research and cohort selection. You do not need to confirm every signal before creating a manual draft for a known contact.

1. **Review suggestions against your business** Open Signals and read suggested traits. Confirm only criteria that actually fit your offer. A suggestion is not a confirmed requirement or a guarantee of a suitable lead.

2. **Build cohorts** Use the cohort builder to combine required and disqualifying traits. Review matching companies in the preview. Changing signals is different from manually adding a contact to a campaign.

3. **Start automation only after suitable setup** Product knowledge, audience, model integration and channels shape the automated agent workflow. Product training is an additional setup process; the dashboard does not replace every advanced configuration step. Review drafts and automated results.

**Outcome and considerations:** Using Help or opening a view does not confirm unconfirmed signals. Manual and automated campaigns can have different technical verification requirements.

## Settings, Controls, Activity and Usage

These four sections distinguish setup, execution and results. An enabled channel does not mean work is currently running. A running agent does not mean every message can send immediately.

| Section / action | Explanation |
| --- | --- |
| Settings | Save mailbox and optional integration credentials; set email channel and daily limit. Geoapify and SerpApi require their own keys; OpenStreetMap does not. Technical verification services are optional additions. Check current provider terms directly; displayed quotas are not a pricing guarantee. |
| Controls → Start / Stop | Start activates the background loop with the current configuration. Stop stops the agent without deleting approvals or stored data. Dashboard website searches are separate jobs with their own Stop control. |
| Activity | Shows logged agent actions with timestamps and action types. A research event is not an email delivery. Use the message’s own status for sending and logs for errors. |
| Usage | Shows available model/subscription usage and quotas. Unavailable data is not the same as zero consumption. Viewing this page does not renew authentication or buy additional allowance. |
| Local data and external services | Contacts and workflow state are stored locally. Depending on the action, public websites, search providers, AI providers or mail services are contacted. Running locally does not mean data never leaves the machine. |

**Outcome and considerations:** This checkout uses harvey.local.yaml as its active local configuration; credentials are managed separately. Help does not display credentials or personal configuration values. Core sending values can be changed in the dashboard, while additional setup may still require the project terminal.

## Solve common problems

Start with the visible symptom. Avoid changing several switches at once: check the named cause, correct it and inspect the status again. This help page does not run searches, approve messages or send mail.

### I cannot select a contact.

Check for a syntactically valid email and a block or opt-out. Add known details using Edit. A person without an email can be stored but cannot receive email. Some stored statuses are not eligible for campaigns; preparation performs additional checks.

### The AI button appears to do nothing.

Fill in offer and goal in the planning fields. The current UI opens that area for missing values and shows an error beside the button. Authentication, quota or unusable AI output produces another message there. Write manually if AI is unavailable.

### My draft is missing from the Outbox.

Save draft alone is not enough. Open the campaign and click Prepare for review beside Save draft. Correct reported contact, placeholder or content issues. Messages for review appear only after preparation succeeds.

### The campaign is no longer editable.

After successful preparation, the campaign is read-only so reviewed text remains stable. Use a new manual draft for different content. Review and reject unwanted old messages in the Outbox; creating a new draft does not automatically remove them.

### The email is yellow rather than green.

Read the text status: Awaiting approval needs your decision. Queued requires a due time and a working agent with enabled, unpaused sending and remaining daily allowance. Use the checklist in “Why an approved email is still waiting”.

### A search finds only a few new companies.

Check raw-record limits, known companies, repeated observations and supported categories. Adjust area, radius, term or source deliberately. A larger limit does not create data or fill gaps in the source.

### I can see an email on the website, but search does not find it.

Check the stored website and actual contact page. Search is bounded and can miss images, protection mechanisms or unusual layouts. Enter a published address manually when needed and retain its source in contact details or notes.

### Codex authentication or a technical check is blocking work.

Read the exact reason in Controls → Logs. For expired authentication, use the project’s existing Codex sign-in, for example scripts/codex login in the project terminal. Changing model, CLI version or isolation rules is not an ordinary toggle-based fix. Do not remove safety checks.

### The updated interface is not visible.

Save open drafts first, then fully reload the website. Refresh in the header normally updates the current section’s data; it does not necessarily reload new JavaScript files.

**Outcome and considerations:** When asking for support, include the section, action, expected result, actual status and relevant error text. Do not share passwords, tokens or OAuth secrets.

## Look up statuses and terms

Different status types describe different things. Email verification describes the address, contact status describes the workflow stage, and message status describes a specific delivery. Keep these separate.

| Term / internal status | Meaning |
| --- | --- |
| Company / contact / campaign | Company as a research record / person or company mailbox as a recipient / collection of recipients and message steps. |
| Unverified · verified · risky | Technical address-check state. Public discovery is not mailbox confirmation. Verification is optional for the manual workflow; automated flows may apply stricter rules. |
| new · queued · company_contact | Contact is new / queued for work / general company contact. A contact marked queued does not prove all of its messages have been approved. |
| contacted · replied · opted_out | Contacted / reply detected / opted out. An opted-out contact remains suppressed; do not use a status change to bypass this. |
| manual_draft · awaiting_review | Editable manual campaign draft / campaign prepared for review and read-only. The latter does not mean every message has been approved or sent. |
| pending_review · approved · sent | Message awaiting approval / approved and scheduled / send accepted by the mail service. |
| failed · rejected · cancelled | Sending failed / rejected by you / cancelled, for example after a contact edit, reply or block. None means successful sending. |
| Block / pause / stop | Blocking applies to a contact or address; sending pause holds delivery; Stop stops the background agent. These controls are not interchangeable. |

**Outcome and considerations:** This guide describes the currently implemented local dashboard. It explains workflows; it does not certify the live state of your mailbox, AI sign-in or a particular recipient.

