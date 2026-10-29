# 06 — Optional Image Factory and private registry

**Start — 2 minutes:** Choose local-only building or the optional independent Factory service.

**You are here:** Optional infrastructure · Factory and registry.

**Done when:** Your complete catalog, authenticated TLS pulls, signatures, and architecture boundaries are verified.

**Skip this chapter** when you only need local image assembly without Factory or Omni.

Standalone Talos users can build locally without Omni or an Image Factory service.
Factory integration provides catalog discovery, schematics, signing, and installer serving.
It does not automatically solve the diagnostic-to-production boot gap.

## 1. Build a complete community catalog

A private registry image is not automatically selectable in Omni.
The pinned community Image Factory can replace the complete core extension catalog through:

```yaml
artifacts:
  core:
    components:
      extensionManifest: readiness/catalog
```

This differs from the Enterprise additive `enterprise.extraExtensions.manifest` feature.
We did not enable or claim Enterprise entitlement.
The replacement catalog must preserve every official extension required by every affected machine.
Our tested catalog covered ten official extensions across seven machines, plus GPU Unlock.
A GPU-only four-extension list is not a safe replacement for a broader active catalog.

<details>
<summary>Catalog file format and entry identity</summary>

The catalog image contains `/image-digests` and `/descriptions.yaml`.
Each digest line uses `registry/repository:version@sha256:digest` syntax.
The custom entry's repository identity is `talos/gpu-unlock`.
Omni reads this catalog through its configured factory and accepts the cataloged namespaced entry.
See the pinned [configuration source](https://github.com/siderolabs/image-factory/blob/45d147aba6b28d66d83a6229f21104d28ddb44a8/docs/configuration.md).

</details>

### Construct the catalog

Export the pinned official catalog through your verified mirror or upstream reference.
Supply its rootfs tar and a complete names inventory to the adapted, tested selection recipe:

```bash
python3 scripts/build-catalog.py YOUR_OFFICIAL_CATALOG_ROOTFS.tar \
  YOUR_COMPLETE_REQUIRED_NAMES.txt \
  'build.example.invalid/talos/gpu-unlock:2.0.0-v1.14.5-r2@sha256:ee0860850fbed0a32222f6b1d380e7eff67454f86019ee4dfa2152ba0f473119' \
  "$PWD/work/catalog"
docker build --platform linux/amd64 -t talos-extension-catalog:v1.14.5 work/catalog
```

The custom digest above identifies the historical private artifact; it is not a public download location.
Use your own built extension digest and matching repository identity when publishing a new catalog.
The catalog contents are data, not an executable GPU module for the factory host.
Mirror each selected extension, the core components, and their signature metadata into the backend paths before promotion.

## 2. Configure the private service boundary

[registry-compose.yaml](../examples/registry-compose.yaml) keeps the registry on `127.0.0.1:5000` with TLS and htpasswd authentication.
Use persistent storage and a separately managed Compose project.
Do not expose the registry publicly or disable its authentication for convenience.

[image-factory.yaml](../examples/image-factory.yaml) uses native HTTPS on port 8443.
It sets `http.certFile`, `http.keyFile`, `http.httpListenAddr`, and `http.externalURL`.
Reserved example addresses and domains must be replaced with your own LAN address and certificate names.
The example leaves `artifacts.installer.external` unset, so installer requests use the factory's native private-backend proxy.
No additional reverse proxy, Kubernetes Gateway, Ingress, or VM is required.
Keep the independent management service on its existing HTTPS port.

Use SSH forwarding for desktop publication:

```bash
ssh -o ExitOnForwardFailure=yes -NT \
  -L 127.0.0.1:5000:127.0.0.1:5000 YOUR_CONFIGURED_FACTORY_SSH_ALIAS
export SSL_CERT_FILE=/absolute/path/to/your/registry-ca.crt
export DOCKER_CONFIG=/absolute/path/to/your/private/docker-auth
```

Configure the registry certificate with the actual local client name in its SANs.
Store credentials outside the repository. Use `docker login --password-stdin` or your credential helper.
These placeholders intentionally do not supply a credential or certificate.

## 3. Build the authenticated TLS proxy patch

The original native OCI proxy stripped caller Authorization headers, then contacted the private backend anonymously.
Installer downloads therefore failed even though the factory could build or locate the image.
The patch resolves backend credentials with the registry keychain and creates an authenticated backend transport.
It requests only the repository pull scope and preserves the configured CA trust.
It does not forward a frontend client's token to the backend.

<details>
<summary>amd64 GPU artifacts and stock arm64 separation</summary>

The same patch skips unsupported platforms while building an OCI index.
A GPU schematic remains amd64-only; it never silently drops GPU Unlock from an arm64 build.
Stock and rollback schematics retain separate amd64 and arm64 manifests.
The factory reads asset files from the imager image rather than executing its amd64 binary.
The pinned imager contains both amd64 and arm64 Talos asset trees.
Our custom image replaces only the amd64 initramfs; stock arm64 kernel and initramfs assets remain unchanged.
The pinned unsupported arm64 GPU request returned HTTP 500; it did not return a stock image.

</details>

Build locally with:

```bash
bash scripts/build-factory.sh "$PWD/work" "$PWD/work/factory"
```

This Factory source requires Go 1.27.0, matching its recorded binary build.
Talos early init uses the separate Go 1.26.8 pin.
The recipe archives pinned source, applies the patch, runs registry/auth tests, and cross-compiles both architectures.
It does not deploy or restart a service.

Read [the actual patch](../patches/image-factory-readiness.patch) and [build-factory.sh](../scripts/build-factory.sh).
Cross-compile the arm64 service binary on the desktop. Do not compile it on the small factory host.
Prebuild amd64 Talos installers locally and populate the signed cache before promoting the service.
On-demand factory cache misses can still perform assembly; do not promise zero CPU work on the service host.

## 4. Verify signatures and publish

Keep `containerSignature.disabled: false`.
Verify official inputs with Sidero's keyless identity and issuer policy, including transparency-log evidence.
Verify custom inputs with an operator-owned public key and preserve discoverable signatures and OCI referrers.
Do not copy another operator's private key, CA, Docker auth directory, or certificate.
The observed signing tool was cosign v3.1.4. Verify flags before using another release.
A recorded official-input verification command is:

```bash
cosign verify \
  --certificate-identity-regexp '(@siderolabs\.com$|^releasemgr-svc@talos-production\.iam\.gserviceaccount\.com$)' \
  --certificate-oidc-issuer https://accounts.google.com \
  'ghcr.io/siderolabs/iscsi-tools:v0.2.0@sha256:584e1d106e424d3e17ddd43bddf892b386748f10d11a9fd024a358f0d42c0a2e'
```

Do not disable transparency verification for these upstream keyless inputs.

Publish the Docker image archive, not its filesystem rootfs tar:

```bash
docker save -o "$PWD/work/extension-image.docker.tar" talos-gpu-unlock:2.0.0-v1.14.5-local
crane push "$PWD/work/extension-image.docker.tar" localhost:5000/talos/gpu-unlock:2.0.0-v1.14.5-local
crane digest localhost:5000/talos/gpu-unlock:2.0.0-v1.14.5-local
crane manifest localhost:5000/talos/gpu-unlock:2.0.0-v1.14.5-local
```

Review redistribution rights before publishing firmware-containing images beyond private use.
The signing example in [sign-private.sh](../scripts/sign-private.sh) preserves the tested local-key workflow.
Its local signatures omit a public transparency service by design; official upstream verification is a separate policy.

## 5. Operate and recover the separate services

Use these Compose commands only for a separately planned service installation, not to modify an existing management deployment:

```bash
docker compose --env-file /absolute/private/registry.env \
  -f examples/registry-compose.yaml config --quiet
docker compose --env-file /absolute/private/registry.env \
  -f examples/registry-compose.yaml up -d
```

Provide `REGISTRY_DIR`, `REGISTRY_PORT=5000`, and `REGISTRY_HTTP_SECRET` outside Git.
Provide `FACTORY_DIR` and a reviewed `FACTORY_IMAGE` for the factory Compose project.
Prepare TLS, htpasswd, backend credentials, CA trust, cache keys, and signed inputs before starting a listener.
Compose configuration validation is not a deployed TLS or signature test.

### Back up and restore

Back up registry data, auth, TLS files, signing keys, and factory configuration together.
Use a consistent stopped-service backup during an approved registry maintenance window.
Test restoration into a different directory and loopback port before replacing the active registry.
Stop or remove only the separate registry/factory Compose projects.
Keep persistent data and preserved installers unless a separate retention decision authorizes deletion.
Never use `docker system prune` as an integration cleanup step.

For an approved registry backup window:

```bash
umask 077
docker compose --env-file /absolute/private/registry.env -f examples/registry-compose.yaml stop registry
tar -C "$REGISTRY_DIR" -cpf "$BACKUP_FILE" data certs auth
cp /absolute/private/registry.env "$BACKUP_ENV_FILE"
docker compose --env-file /absolute/private/registry.env -f examples/registry-compose.yaml start registry
sha256sum "$BACKUP_FILE" "$BACKUP_ENV_FILE"
```

Protect the backup and environment file as credentials. Back up factory configuration, trust, and signing keys separately.
Restore into a new directory, never directly over active data.
A parallel restoration test needs different loopback service **and debug ports**, such as 15000 and 15001.
It also needs a separate Compose project name and the restored upload-session secret.
Verify authenticated TLS manifest pulls and signatures before any promotion.
To remove a service, stop only its separate Compose project and retain its persistent directory and backups.
No removal or backup command above ran during documentation finalization.

Treat published input tags and catalog contents as immutable.
A reviewed rebuild needs a distinct repository/cache scope and verification of resolved input and output digests.
Do not assume a mutable catalog tag forces cached installers to rebuild.

---

[Guide home](../README.md) · **Next — 2 minutes:** [open the Omni desired-versus-running check](07-omni.md).
