// V4: Bump seed canonicalization - Instance 2 (PATCHED)
// Fix: remove user_bump parameter; store bump from ctx.bumps (canonical).
// Use bump = user_account.bump only after the canonical value is saved.

use anchor_lang::prelude::*;

declare_id!("USERPDA11111111111111111111111111111111111");

#[program]
pub mod user_registry {
    use super::*;

    pub fn register_user(ctx: Context<RegisterUser>, username: String) -> Result<()> {
        let user_account = &mut ctx.accounts.user_account;
        user_account.owner = ctx.accounts.payer.key();
        user_account.username = username;
        // FIX: canonical bump from find_program_address via Anchor's seeds+bump.
        user_account.bump = *ctx.bumps.get("user_account").unwrap();
        user_account.balance = 0;
        Ok(())
    }

    pub fn credit(ctx: Context<UserAction>, amount: u64) -> Result<()> {
        ctx.accounts.user_account.balance = ctx
            .accounts
            .user_account
            .balance
            .checked_add(amount)
            .ok_or(RegistryError::Overflow)?;
        Ok(())
    }
}

#[derive(Accounts)]
pub struct RegisterUser<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + UserAccount::SIZE,
        seeds = [b"user", payer.key().as_ref()],
        bump
    )]
    pub user_account: Account<'info, UserAccount>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct UserAction<'info> {
    #[account(
        mut,
        seeds = [b"user", user.key().as_ref()],
        bump = user_account.bump
    )]
    pub user_account: Account<'info, UserAccount>,
    pub user: Signer<'info>,
}

#[account]
pub struct UserAccount {
    pub owner: Pubkey,
    pub username: String,
    pub balance: u64,
    pub bump: u8,
}

impl UserAccount {
    pub const SIZE: usize = 32 + 64 + 8 + 1;
}

#[error_code]
pub enum RegistryError {
    #[msg("Arithmetic overflow")]
    Overflow,
}
