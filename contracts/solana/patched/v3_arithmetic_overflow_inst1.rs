// V3: Arithmetic overflow on u64 - Instance 1 (PATCHED)
// Fix: use checked_mul and checked_div; return error on overflow.

use anchor_lang::prelude::*;

declare_id!("YIELD111111111111111111111111111111111111111");

const RATE_DENOMINATOR: u64 = 10_000;

#[program]
pub mod yield_vault {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, annual_rate_bps: u64) -> Result<()> {
        let vault = &mut ctx.accounts.vault;
        vault.annual_rate_bps = annual_rate_bps;
        vault.total_deposits = 0;
        vault.bump = *ctx.bumps.get("vault").unwrap();
        Ok(())
    }

    pub fn deposit(ctx: Context<VaultAction>, amount: u64) -> Result<()> {
        ctx.accounts.vault.total_deposits = ctx
            .accounts
            .vault
            .total_deposits
            .checked_add(amount)
            .ok_or(VaultError::Overflow)?;
        Ok(())
    }

    pub fn withdraw_with_yield(ctx: Context<VaultAction>, amount: u64) -> Result<()> {
        let rate = ctx.accounts.vault.annual_rate_bps;

        // FIX: checked_mul prevents wrapping; error returned on overflow.
        let yield_amount = amount
            .checked_mul(rate)
            .ok_or(VaultError::Overflow)?
            .checked_div(RATE_DENOMINATOR)
            .ok_or(VaultError::Overflow)?;

        let total_out = amount.checked_add(yield_amount).ok_or(VaultError::Overflow)?;

        require!(
            ctx.accounts.vault.total_deposits >= total_out,
            VaultError::InsufficientFunds
        );
        ctx.accounts.vault.total_deposits -= total_out;
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + Vault::SIZE,
        seeds = [b"vault"],
        bump
    )]
    pub vault: Account<'info, Vault>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct VaultAction<'info> {
    #[account(mut, seeds = [b"vault"], bump = vault.bump)]
    pub vault: Account<'info, Vault>,
    pub user: Signer<'info>,
}

#[account]
pub struct Vault {
    pub annual_rate_bps: u64,
    pub total_deposits: u64,
    pub bump: u8,
}

impl Vault {
    pub const SIZE: usize = 8 + 8 + 1;
}

#[error_code]
pub enum VaultError {
    #[msg("Insufficient vault funds")]
    InsufficientFunds,
    #[msg("Arithmetic overflow")]
    Overflow,
}
