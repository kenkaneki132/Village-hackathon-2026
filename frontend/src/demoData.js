// Synthetic demo scenarios used when the app runs without a backend (e.g. GitHub Pages).
// All people, IDs and addresses are fictional. Dates are computed relative to today so
// expiration logic always looks current.

const iso = (d) => d.toISOString().slice(0, 10)
const daysFromNow = (n) => { const d = new Date(); d.setDate(d.getDate() + n); return d }

const check = (check, result, detail) => ({ check, result, detail })
const flag = (severity, message, rule_citation, category) => ({ severity, message, rule_citation, category })

function warnScenario() {
  const exp = daysFromNow(12)
  return {
    level1: {
      verdict: 'WARN',
      verdict_message: 'Document appears genuine with minor inconsistencies in font rendering on the DOB field.',
      authenticity_score: 0.74,
      checks: [
        check('Font Consistency', 'WARN', 'DOB field uses slightly lighter weight than adjacent fields — possible reprint artifact'),
        check('Field Format Validation', 'PASS', 'All field formats match Colorado DL standards (AAMVA 2020)'),
        check('Security Features', 'PASS', 'Ghost image present, holographic overlay visible, microprint zone intact'),
        check('Layout/AAMVA Compliance', 'PASS', 'Field zones and barcode placement conform to AAMVA D20 layout'),
        check('MRZ Integrity', 'WARN', 'PDF417 barcode partially obscured — could not fully verify checksum'),
      ],
      flags: [
        { severity: 'WARN', message: 'DOB font weight inconsistency — recommend manual secondary check' },
        { severity: 'WARN', message: 'PDF417 barcode partially unreadable — request alternative ID if possible' },
        { severity: 'OK', message: 'No signs of digital manipulation or layer artifacts detected' },
      ],
      suspicious_elements: ['DOB font weight', 'PDF417 partial occlusion'],
    },
    level2: {
      extracted_fields: {
        first_name: 'Jane', last_name: 'Doe', dob: '1985-04-12', id_number: 'D123-456-78-901-0',
        expiration: iso(exp), address: '1420 Elm St, Denver CO 80203', license_class: 'D',
        issuing_state: 'CO', issuing_country: 'USA', gender: 'F', height: '5-06', eye_color: 'BRN',
      },
      extraction_confidence: 0.88,
      field_confidences: { first_name: 0.97, last_name: 0.97, dob: 0.91, id_number: 0.85, expiration: 0.94, address: 0.82 },
      ocr_issues: ['ID number partially obscured by glare', 'Address line 2 not present'],
    },
    level3: {
      cross_doc_available: true,
      comparisons: [
        { field: 'last_name', id_value: 'Doe', doc_value: 'Doe', match: true, confidence: 0.99, flag: 'MATCH' },
        { field: 'first_name', id_value: 'Jane', doc_value: 'Jennifer', match: false, confidence: 0.61, flag: 'PARTIAL_MATCH' },
        { field: 'dob', id_value: '1985-04-12', doc_value: '1985-04-12', match: true, confidence: 0.99, flag: 'MATCH' },
        { field: 'address', id_value: '1420 Elm St, Denver CO 80203', doc_value: '1420 Elm Street, Denver, CO 80203', match: true, confidence: 0.93, flag: 'MATCH' },
        { field: 'id_number', id_value: 'D123-456-78-901-0', doc_value: null, match: false, confidence: 0, flag: 'UNAVAILABLE' },
      ],
      overall_match_score: 0.81,
      identity_consistency: 'PARTIAL',
    },
    level4: {
      compliance_verdict: 'WARN',
      compliance_flags: [
        flag('WARN', '⚠ ID expires in 12 days — verify acceptability with signing parties', 'General notary best practice', 'EXPIRATION'),
        flag('WARN', "First name partial match: 'Jane' (ID) vs 'Jennifer' (loan app) — confirm legal name with signer", 'MISMO closing requirements', 'NAME_MATCH'),
        flag('OK', 'In-state ID confirmed for Colorado property transaction', 'CO Rev. Stat. § 12-55-110', 'IN_STATE'),
        flag('OK', 'License class D is valid for standard identification purposes', 'AAMVA DL/ID Card Design Standard', 'FORMAT'),
      ],
      expiration_status: { is_expired: false, days_until_expiry: 12, status: 'EXPIRING_SOON' },
      overall_recommendation: 'HOLD',
      recommendation_detail: "Proceed with caution — confirm signer's legal name matches loan documents and flag expiring ID in closing package per MISMO requirements.",
    },
    summary: {
      overall_verdict: 'WARN',
      risk_level: 'MEDIUM',
      key_findings: [
        'ID expires in 12 days — must be noted in closing package',
        "First name 'Jane' vs 'Jennifer' on loan app — likely nickname, confirm with signer",
        'PDF417 barcode partially unreadable — recommend secondary ID if available',
        'DOB and address match across documents',
        'No signs of document forgery detected',
      ],
      notary_action: "Request signer confirm legal name 'Jennifer'; note expiring ID in closing package; proceed if name confirmed and second ID available.",
    },
    processing_time_ms: 3241,
  }
}

function passScenario() {
  const exp = daysFromNow(3 * 365 + 40)
  const days = Math.round((exp - new Date()) / 864e5)
  return {
    level1: {
      verdict: 'PASS',
      verdict_message: 'All authenticity checks passed; no signs of tampering.',
      authenticity_score: 0.96,
      checks: [
        check('Font Consistency', 'PASS', 'Uniform typeface and weight across all printed fields'),
        check('Field Format Validation', 'PASS', 'ID number, dates and class match Arizona DL formats'),
        check('Security Features', 'PASS', 'Ghost portrait, UV-reactive seal pattern and microprint present'),
        check('Layout/AAMVA Compliance', 'PASS', 'Layout matches AAMVA 2020 card design standard'),
        check('MRZ Integrity', 'PASS', 'PDF417 barcode decoded; data matches printed fields'),
      ],
      flags: [{ severity: 'OK', message: 'No authenticity concerns detected' }],
      suspicious_elements: [],
    },
    level2: {
      extracted_fields: {
        first_name: 'Marcus', last_name: 'Rivera', dob: '1992-09-03', id_number: 'D08814527',
        expiration: iso(exp), address: '845 E University Dr, Tempe AZ 85281', license_class: 'D',
        issuing_state: 'AZ', issuing_country: 'USA', gender: 'M', height: '5-11', eye_color: 'HAZ',
      },
      extraction_confidence: 0.97,
      field_confidences: { first_name: 0.99, last_name: 0.99, dob: 0.98, id_number: 0.97, expiration: 0.98, address: 0.94 },
      ocr_issues: [],
    },
    level3: {
      cross_doc_available: true,
      comparisons: [
        { field: 'last_name', id_value: 'Rivera', doc_value: 'Rivera', match: true, confidence: 0.99, flag: 'MATCH' },
        { field: 'first_name', id_value: 'Marcus', doc_value: 'Marcus', match: true, confidence: 0.99, flag: 'MATCH' },
        { field: 'dob', id_value: '1992-09-03', doc_value: '1992-09-03', match: true, confidence: 0.99, flag: 'MATCH' },
        { field: 'address', id_value: '845 E University Dr, Tempe AZ 85281', doc_value: '845 East University Drive, Tempe, AZ 85281', match: true, confidence: 0.95, flag: 'MATCH' },
      ],
      overall_match_score: 0.98,
      identity_consistency: 'CONSISTENT',
    },
    level4: {
      compliance_verdict: 'PASS',
      compliance_flags: [
        flag('OK', 'ID is valid and not near expiration', 'NIST SP 800-63-3 IAL2', 'EXPIRATION'),
        flag('OK', 'Name matches supporting document exactly', 'MISMO closing requirements', 'NAME_MATCH'),
        flag('OK', 'In-state ID for Arizona transaction', 'A.R.S. § 41-311', 'IN_STATE'),
      ],
      expiration_status: { is_expired: false, days_until_expiry: days, status: 'VALID' },
      overall_recommendation: 'PROCEED',
      recommendation_detail: 'All four levels passed. Record ID type, number and expiration in the journal and proceed with signing.',
    },
    summary: {
      overall_verdict: 'PASS',
      risk_level: 'LOW',
      key_findings: [
        'All authenticity checks passed (score 0.96)',
        'All fields extracted with ≥ 94% confidence',
        'Identity consistent across ID and utility bill',
        `ID valid for ${days} more days`,
      ],
      notary_action: 'Proceed with notarization; record ID details in the notary journal.',
    },
    processing_time_ms: 2876,
  }
}

function failScenario() {
  const exp = daysFromNow(-94)
  return {
    level1: {
      verdict: 'FAIL',
      verdict_message: 'Multiple indicators of digital alteration in the portrait and date fields.',
      authenticity_score: 0.21,
      checks: [
        check('Font Consistency', 'FAIL', 'Expiration date rendered in a different typeface (sans vs. state-standard condensed)'),
        check('Field Format Validation', 'FAIL', 'ID number has 10 digits; Texas DL numbers are 8 digits'),
        check('Security Features', 'FAIL', 'Ghost portrait missing; holographic overlay not visible'),
        check('Layout/AAMVA Compliance', 'WARN', 'Signature block shifted ~3mm from standard position'),
        check('MRZ Integrity', 'FAIL', 'PDF417 data (DOB 1979) does not match printed DOB (1988)'),
      ],
      flags: [
        { severity: 'ERROR', message: 'Barcode-encoded DOB contradicts printed DOB — strong forgery signal' },
        { severity: 'ERROR', message: 'Portrait region shows compression boundary consistent with photo substitution' },
        { severity: 'WARN', message: 'Edge sharpness inconsistent with card stock' },
      ],
      suspicious_elements: ['Portrait substitution', 'Expiration date font', 'Barcode/print DOB mismatch', 'ID number length'],
    },
    level2: {
      extracted_fields: {
        first_name: 'Daniel', last_name: 'Okafor', dob: '1988-02-17', id_number: '4471920036',
        expiration: iso(exp), address: '2200 Main St, Houston TX 77002', license_class: 'C',
        issuing_state: 'TX', issuing_country: 'USA', gender: 'M', height: '6-01', eye_color: 'BRO',
      },
      extraction_confidence: 0.79,
      field_confidences: { first_name: 0.95, last_name: 0.93, dob: 0.62, id_number: 0.71, expiration: 0.83, address: 0.88 },
      ocr_issues: ['DOB conflicts with barcode payload', 'Expiration field shows resampling artifacts'],
    },
    level3: {
      cross_doc_available: true,
      comparisons: [
        { field: 'last_name', id_value: 'Okafor', doc_value: 'Okafor', match: true, confidence: 0.97, flag: 'MATCH' },
        { field: 'first_name', id_value: 'Daniel', doc_value: 'Daniel', match: true, confidence: 0.97, flag: 'MATCH' },
        { field: 'dob', id_value: '1988-02-17', doc_value: '1979-02-17', match: false, confidence: 0.12, flag: 'MISMATCH' },
        { field: 'address', id_value: '2200 Main St, Houston TX 77002', doc_value: '918 Bayou Rd, Galveston TX 77550', match: false, confidence: 0.08, flag: 'MISMATCH' },
      ],
      overall_match_score: 0.34,
      identity_consistency: 'INCONSISTENT',
    },
    level4: {
      compliance_verdict: 'FAIL',
      compliance_flags: [
        flag('ERROR', 'ID is expired (expired 94 days ago) — automatic FAIL under NIST IAL2', 'NIST SP 800-63-3 IAL2', 'EXPIRATION'),
        flag('ERROR', 'DOB on ID does not match DOB on deed of trust', 'MISMO closing requirements', 'NAME_MATCH'),
        flag('WARN', 'Texas property transaction requires in-state ID — ID is TX but authenticity failed', 'Tex. Gov. Code § 406.014', 'IN_STATE'),
      ],
      expiration_status: { is_expired: true, days_until_expiry: -94, status: 'EXPIRED' },
      overall_recommendation: 'REJECT',
      recommendation_detail: 'Do not proceed. Document shows forgery indicators, is expired, and conflicts with the supporting document.',
    },
    summary: {
      overall_verdict: 'FAIL',
      risk_level: 'CRITICAL',
      key_findings: [
        'Barcode DOB (1979) contradicts printed DOB (1988)',
        'Portrait substitution artifacts detected',
        'ID expired 94 days ago',
        'Address and DOB mismatch with deed of trust',
      ],
      notary_action: 'Refuse notarization. Document the refusal in the journal and do not return the reason to the signer in detail.',
    },
    processing_time_ms: 3518,
  }
}

export const DEMO_SCENARIOS = [
  { id: 'pass', label: 'Clean ID', emoji: '✅', hint: 'Valid AZ license, all levels pass', build: passScenario },
  { id: 'warn', label: 'Needs review', emoji: '⚠️', hint: 'Expiring soon + nickname mismatch', build: warnScenario },
  { id: 'fail', label: 'Forged & expired', emoji: '⛔', hint: 'Tampering signals, cross-doc mismatch', build: failScenario },
]

export const getScenario = (id) => (DEMO_SCENARIOS.find((s) => s.id === id) || DEMO_SCENARIOS[1]).build()
