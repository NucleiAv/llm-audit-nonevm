// V4: Bump seed canonicalization - Instance 3 (variant)
// Subtler: canonical bump IS stored, but the verification instruction
// re-derives using create_program_address with the stored bump without
// ensuring it matches the canonical bump from find_program_address.
// An attacker who stores a non-canonical bump during a separate init path
// can later pass validation because the stored bump re-derives a valid PDA.

use anchor_lang::prelude::*;
use anchor_lang::solana_program::pubkey::Pubkey as SolanaPubkey;

declare_id!("BUMPV3111111111111111111111111111111111111");

#[program]
pub mod escrow {
    use super::*;

    pub fn initialize_escrow(
        ctx: Context<InitEscrow>,
        escrow_bump: u8,
        amount: u64,
    ) -> Result<()> {
        let escrow = &mut ctx.accounts.escrow;
        // BUG: stores caller-supplied bump, not the canonical bump.
        escrow.bump = escrow_bump;
        escrow.depositor = ctx.accounts.depositor.key();
        escrow.amount = amount;
        Ok(())
    }

    pub fn release_escrow(ctx: Context<ReleaseEscrow>) -> Result<()> {
        let escrow = &ctx.accounts.escrow;

        // BUG: re-derives PDA using stored (potentially non-canonical) bump.
        // A non-canonical bump still produces a valid PDA, so this check passes
        // for an attacker-created escrow account with a crafted bump value.
        let expected = SolanaPubkey::create_program_address(
            &[
                b"escrow",
                escrow.depositor.as_ref(),
                &[escrow.bump],
            ],
            ctx.program_id,
        )
        .map_err(|_| error!(EscrowError::InvalidEscrow))?;

        require!(
            ctx.accounts.escrow.key() == expected,
            EscrowError::InvalidEscrow
        );

        Ok(())
    }
}

#[derive(Accounts)]
pub struct InitEscrow<'info> {
    #[account(mut)]
    pub escrow: AccountInfo<'info>,
    pub depositor: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ReleaseEscrow<'info> {
    #[account(mut)]
    pub escrow: Account<'info, Escrow>,
    pub depositor: Signer<'info>,
}

#[account]
pub struct Escrow {
    pub depositor: Pubkey,
    pub amount: u64,
    pub bump: u8,
}

#[error_code]
pub enum EscrowError {
    #[msg("Invalid escrow account")]
    InvalidEscrow,
}
