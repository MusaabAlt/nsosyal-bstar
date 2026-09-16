import generated from './labels.generated.json'
import type { Action, ContentCode, Family, FormCode, GuardCode, ModuleName, TargetType } from './types'

/*
 * Turkish labels, generated from AI/contracts/codes.py (TR_LABELS) by
 * scripts/gen-labels.mjs. The response carries codes only; this is the one
 * place the screen turns a code into Turkish.
 */
const labels = generated.labels as Record<string, Record<string, string>>

function label(enumName: string, value: string): string {
  // An unknown code shows as itself rather than disappearing.
  return labels[enumName]?.[value] ?? value
}

export const contentLabel = (code: ContentCode | string) => label('ContentCode', code)
export const formLabel = (code: FormCode | string) => label('FormCode', code)
export const guardLabel = (code: GuardCode | string) => label('GuardCode', code)
export const targetLabel = (type: TargetType | string) => label('TargetType', type)
export const familyLabel = (family: Family | string) => label('Family', family)

export const CONTENT_CODES = Object.values(generated.enums.ContentCode) as ContentCode[]
export const FAMILIES = Object.values(generated.enums.Family) as Family[]
export const MODULE_NAMES = Object.values(generated.enums.ModuleName) as ModuleName[]
export const ACTIONS = Object.values(generated.enums.Action) as Action[]

/** A content code's family is its first letter; CLEAN is its own family (codes.py FAMILY). */
export function familyOf(code: ContentCode): Family {
  return code === 'CLEAN' ? 'CLEAN' : (code[0] as Family)
}
export const actionLabel = (action: Action | string) => label('Action', action)
