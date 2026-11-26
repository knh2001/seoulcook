# Inquiry delivery — pending account configuration

This Worker handles both `POST /api/inquiry` and inbound mail addressed to the public export address. It has not been deployed or connected to production. The two destination addresses belong only in the runtime secret `INQUIRY_RECIPIENTS`, as a JSON array of two distinct verified addresses. Do not add destinations or credentials to the website repository.

The HTTP handler submits one message addressed to both destinations. The inbound email handler forwards the original message to both verified destinations, retaining its body and attachments. A loop marker blocks repeated forwarding. No application database or message-body logging is added. Provider acceptance is not proof of inbox delivery.

## Account checks before deployment

1. Inspect existing `export` and destination-domain routing, including catch-all rules. Record the previous export rule privately for rollback. Confirm the requested same-domain destination is a functioning mailbox or safe route, rather than an alias returning to export or a duplicate route to the other destination.
2. Verify both destination addresses in Cloudflare Email Routing. Complete any mailbox confirmation messages. A pending destination is not verified.
3. Confirm the domain is enabled for Email Sending with the verified-destination free tier. Do not purchase or upgrade a plan.
4. Create the Turnstile widget for `seoulcook.com` and `www.seoulcook.com`. Store its secret only as `TURNSTILE_SECRET_KEY`; its public key is `TURNSTILE_SITE_KEY`. No authentication tokens belong in browser source or repository files.
5. Deploy using the existing account and the `wrangler.jsonc` bindings, initially disabled. Set `INQUIRY_RECIPIENTS` privately and enable only after all bindings are present. Attach the domain routes only when the account is correct. Do not change unrelated website or DNS routes.
6. Publish the confirmed processing-service and security-check notice in the KO/EN privacy policy before activating the new form. The existing policy currently describes mail-client submission and advance notice of changes; reconcile its effective date and notice process before rollout. The repository's current privacy page is intentionally unchanged pending actual service configuration.
7. Test a synthetic HTTP inquiry and an inbound export message to the two authorized destinations. Check actual delivery separately from API acceptance. Check reply-to, attachment preservation, spam folders, loops and duplicate alias routing. Then switch the single export rule to this Worker; Cloudflare uses only the first matching custom-address rule.
8. Publish the contact/B2B form changes only with a healthy backend and current privacy notice. Verify KO/EN success/failure states on the live site. The local form draft disables submission when configuration or the security check is unavailable and always offers a direct email link.

## Verification

Run `node --test tests/inquiry.test.mjs tests/inquiry-client.test.mjs` from the repository root. These tests use fake destinations and a mocked provider; they do not claim real email delivery. Run Wrangler's `deploy --dry-run --config workers/inquiry/wrangler.jsonc` to validate bundling and bindings without changing the account. Keep generated bundles outside the public site tree.

## Rollback

Restore the recorded export routing action, roll back the two frontend pages to the previous Pages deployment, set `INQUIRY_ENABLED=false`, and remove only the newly created `/api/inquiry*` Worker routes. Retain all unrelated mail and website settings. Preserve the private before/after record without credentials. Review any partially forwarded test before retrying, since provider errors or network interruptions can leave delivery uncertain.

## Official implementation references

- [Worker email sending API](https://developers.cloudflare.com/email-service/api/send-emails/workers-api/)
- [Inbound email Worker handler](https://developers.cloudflare.com/email-service/api/route-emails/email-handler/)
- [Custom address routing rules](https://developers.cloudflare.com/email-service/configuration/email-routing-addresses/)
- [Destination verification](https://developers.cloudflare.com/email-service/configuration/destination-addresses/)
- [Turnstile server validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)
- [Rate limit binding](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/)
