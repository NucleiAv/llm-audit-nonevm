// V3: Arithmetic overflow on u64 - Instance 3 (PATCHED)
// Fix: checked_add on both accumulations; error on overflow.

use anchor_lang::prelude::*;

declare_id!("SHARES11111111111111111111111111111111111111");

#[program]
pub mod share_vault {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        let vault = &mut ctx.accounts.vault;
        vault.shares_outstanding = 0;
        vault.total_assets = 0;
        vault.bump = *ctx.bumps.get("vault").unwrap();
        Ok(())
    }

    pub fn issue_shares(ctx: Context<VaultAction>, new_shares: u64) -> Result<()> {
        let vault = &mut ctx.accounts.vault;
        // FIX: checked_add prevents silent wrap-around.
        vault.shares_outstanding = vault
            .shares_outstanding
            .checked_add(new_shares)
            .ok_or(VaultError::Overflow)?;
        vault.total_assets = vault
            .total_assets
            .checked_add(new_shares)
            .ok_or(VaultError::Overflow)?;
        Ok(())
    }

    pub fn get_share_price(ctx: Context<VaultAction>) -> Result<u64> {
        let vault = &ctx.accounts.vault;
        if vault.shares_outstanding == 0 {
            return Ok(1);
        }
        Ok(vault.total_assets / vault.shares_outstanding)
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
    pub shares_outstanding: u64,
    pub total_assets: u64,
    pub bump: u8,
}

impl Vault {
    pub const SIZE: usize = 8 + 8 + 1;
}

#[error_code]
pub enum VaultError {
    #[msg("Arithmetic overflow")]
    Overflow,
}
