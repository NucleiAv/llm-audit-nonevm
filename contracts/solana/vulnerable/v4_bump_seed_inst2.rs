// V4: Bump seed canonicalization - Instance 2
// Pattern: User account PDA created with a user-controlled seed component
// AND a user-supplied bump. Allows creating duplicate account slots for
// the same user seed by varying the bump.

use anchor_lang::prelude::*;

declare_id!("USERPDA11111111111111111111111111111111111");

#[program]
pub mod user_registry {
    use super::*;

    // BUG: user_bump is caller-supplied and never verified as canonical.
    // An attacker can create multiple "user" PDAs for the same wallet
    // by calling this function with different bump values, each producing
    // a valid (non-canonical) PDA — enabling duplicate account confusion.
    pub fn register_user(
        ctx: Context<RegisterUser>,
        username: String,
        user_bump: u8,
    ) -> Result<()> {
        let user_account = &mut ctx.accounts.user_account;
        user_account.owner = ctx.accounts.payer.key();
        user_account.username = username;
        user_account.bump = user_bump; // BUG: stores non-canonical bump
        user_account.balance = 0;
        Ok(())
    }

    pub fn credit(ctx: Context<UserAction>, amount: u64) -> Result<()> {
        ctx.accounts.user_account.balance = ctx
            .accounts
            .user_account
            .balance
            .wrapping_add(amount);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct RegisterUser<'info> {
    // BUG: init_if_needed with caller-supplied bump means multiple accounts
    // can exist for the same owner seed with different bumps.
    #[account(
        init_if_needed,
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
    // BUG: bump = user_account.bump uses whatever bump was stored,
    // which may be non-canonical if the attacker stored it that way.
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
