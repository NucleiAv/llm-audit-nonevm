// V3: Arithmetic overflow on u64 - Instance 1
// Pattern: Token yield calculation uses unchecked multiplication on u64.
// In Solana release builds, u64 arithmetic wraps on overflow.
// An attacker passes amount = u64::MAX / rate + 1, causing yield to wrap
// to a small number and allowing withdrawal of a disproportionate share.
// Source: Sec3 Solana audit methodology, OWASP Smart Contract Top 10 2025.

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
            .wrapping_add(amount);
        Ok(())
    }

    // BUG: unchecked multiplication on u64 — wraps in release build.
    // If amount * annual_rate_bps overflows u64, yield_amount wraps to
    // a small value, allowing draining the vault at minimal cost.
    pub fn withdraw_with_yield(ctx: Context<VaultAction>, amount: u64) -> Result<()> {
        let rate = ctx.accounts.vault.annual_rate_bps;

        // Overflow possible: amount * rate overflows u64 when amount is large.
        let yield_amount = amount * rate / RATE_DENOMINATOR;
        let total_out = amount + yield_amount;

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
}
