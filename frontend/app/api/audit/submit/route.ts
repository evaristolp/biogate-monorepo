import { createClient } from "@supabase/supabase-js"
import { createClient as createServerClient } from "@/lib/supabase/server"
import { NextResponse } from "next/server"

export async function POST(request: Request) {
  // Verify the user is authenticated
  const supabaseAuth = await createServerClient()
  const {
    data: { user },
  } = await supabaseAuth.auth.getUser()

  if (!user) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 })
  }

  // Create a service role client to bypass RLS
  const supabaseAdmin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_MONOREPO_URL!,
    process.env.SUPABASE_MONOREPO_SERVICE_ROLE_KEY!
  )

  try {
    const formData = await request.formData()
    const reportEmail = formData.get("reportEmail") as string
    const file = formData.get("file") as File

    if (!file || !reportEmail) {
      return NextResponse.json(
        { error: "Missing file or email" },
        { status: 400 }
      )
    }

    // Create an audit entry
    const { data: audit, error: auditError } = await supabaseAdmin
      .from("audits")
      .insert({
        organization_id: null,
        status: "pending",
      })
      .select("id")
      .single()

    if (auditError) {
      return NextResponse.json({ error: auditError.message }, { status: 500 })
    }

    // Ensure the vendor-lists bucket exists
    const { data: buckets } = await supabaseAdmin.storage.listBuckets()
    const bucketExists = buckets?.some((b) => b.name === "vendor-lists")
    if (!bucketExists) {
      await supabaseAdmin.storage.createBucket("vendor-lists", {
        public: false,
        fileSizeLimit: 10485760, // 10MB
      })
    }

    // Upload the file to Supabase storage
    const filePath = `${user.id}/${audit.id}/${file.name}`
    const fileBuffer = Buffer.from(await file.arrayBuffer())

    const { error: uploadError } = await supabaseAdmin.storage
      .from("vendor-lists")
      .upload(filePath, fileBuffer, {
        contentType: file.type,
      })

    if (uploadError) {
      return NextResponse.json({ error: uploadError.message }, { status: 500 })
    }

    // Record the document upload
    const { error: docError } = await supabaseAdmin
      .from("document_uploads")
      .insert({
        audit_id: audit.id,
        original_filename: file.name,
        mime_type: file.type,
        file_size_bytes: file.size,
        s3_key: filePath,
        extraction_method: "pending",
      })

    if (docError) {
      return NextResponse.json({ error: docError.message }, { status: 500 })
    }

    return NextResponse.json({ auditId: audit.id, email: reportEmail })
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Server error" },
      { status: 500 }
    )
  }
}
