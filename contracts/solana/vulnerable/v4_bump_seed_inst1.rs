// V4: Bump seed canonicalization - Instance 1
// Source: Anchor security documentation, coral-xyz/sealevel-attacks repo.
// Vulnerability: Using create_program_address with a caller-supplied bump
// instead of find_program_address means an attacker can supply any valid
// (non-canonical) bump to derive an alternative PDA, then use it as if
// it were the authoritative program account.

use anchor_lang::prelude::*;
use anchor_lang::solana_program::program_error::ProgramError;

declare_id!("BUMP1111111111111111111111111111111111111111");

#[program]
pub mod bump_vuln {
    use super::*;

    // BUG: accepts caller-supplied bump — does not verify it is canonical.
    // An attacker can precompute a non-canonical bump that derives a
    // different valid PDA, allowing them to hijack a privileged account slot.
    pub fn create_config(ctx: Context<CreateConfig>, user_supplied_bump: u8) -> Result<()> {
        let seeds = &[b"config".as_ref(), &[user_supplied_bump]];

        // Dangerous: create_program_address does not enforce bump canonicity.
        let (derived_key, _) =
            anchor_lang::solana_program::pubkey::Pubkey::find_program_address(
                &[b"config"],
                ctx.program_id,
            );

        // The check below is bypassed when attacker provides a non-canonical bump
        // that also derives a valid (different) PDA — both pass create_program_address.
        require!(
            ctx.accounts.config.key() == derived_key || {
                // BUG: fallback accepts any bump that produces a valid PDA.
                let alt = anchor_lang::solana_program::pubkey::Pubkey::create_program_address(
                    seeds,
                    ctx.program_id,
                )
                .map_err(|_| error!(BumpError::InvalidBump))?;
                ctx.accounts.config.key() == alt
            },
            BumpError::InvalidBump
        );

        let config = &mut ctx.accounts.config;
        config.bump = user_supplied_bump;
        config.authority = ctx.accounts.payer.key();
        Ok(())
    }
}

#[derive(Accounts)]
pub struct CreateConfig<'info> {
    #[account(mut)]
    pub config: AccountInfo<'info>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[account]
pub struct Config {
    pub bump: u8,
    pub authority: Pubkey,
}

#[error_code]
pub enum BumpError {
    #[msg("Invalid bump seed")]
    InvalidBump,
}
